"""
Database connection and operations for TechStack Scout.
Supports both PostgreSQL (via asyncpg) and SQLite (via aiosqlite).
"""

import os
import sys
import re
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

# Connection string defaults to a local SQLite database for easy development
if sys.platform == "win32":
    user_profile = os.environ.get("USERPROFILE", "C:/Users/mahad")
    db_dir = os.path.join(user_profile, ".gemini", "antigravity-cli")
    os.makedirs(db_dir, exist_ok=True)
    default_db_path = os.path.join(db_dir, "techstack_scout.db").replace("\\", "/")
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///techstack_scout.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# Import the appropriate library based on database type
if IS_SQLITE:
    import aiosqlite
else:
    import asyncpg

_pool: Optional[Any] = None


def translate_query(query: str) -> str:
    """Translate PostgreSQL query syntax to SQLite syntax if needed."""
    if not IS_SQLITE:
        return query
        
    # Replace $1, $2, etc. with :p1, :p2, etc. for SQLite named parameter binding
    query = re.sub(r'\$(\d+)', r':p\1', query)
    
    # Translate interval subtraction: NOW() - INTERVAL 'X units' -> datetime('now', '-X units')
    query = re.sub(r"NOW\(\)\s*-\s*INTERVAL\s*'(\d+)\s+(\w+)'", r"datetime('now', '-\1 \2')", query)
    
    # Replace PostgreSQL-specific date/time functions
    query = query.replace("NOW()", "datetime('now')")
    
    # Replace ILIKE with LIKE (SQLite LIKE is case-insensitive by default)
    query = query.replace("ILIKE", "LIKE")
    
    # Remove NULLS LAST/FIRST (SQLite 3.30+ supports it, but removing it is safer for compatibility)
    query = query.replace("NULLS LAST", "")
    query = query.replace("NULLS FIRST", "")
    
    return query


class SQLitePoolWrapper:
    """Wrapper that mimics asyncpg.Pool interface for aiosqlite."""
    
    def __init__(self, db_path: str):
        # Strip sqlite:/// prefix if present
        if db_path.startswith("sqlite:///"):
            self.db_path = db_path[10:]
        elif db_path.startswith("sqlite://"):
            self.db_path = db_path[9:]
        else:
            self.db_path = db_path
            
    @asynccontextmanager
    async def acquire(self):
        # Open connection
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        # Enable foreign key support
        await conn.execute("PRAGMA foreign_keys = ON")
        
        class SQLiteConnectionWrapper:
            def __init__(self, c):
                self._c = c
                
            async def execute(self, query: str, *args):
                sql = translate_query(query)
                params = {f"p{i+1}": val for i, val in enumerate(args)}
                cursor = await self._c.execute(sql, params)
                await self._c.commit()
                return cursor
                
            async def executemany(self, query: str, args_list: List[Any]):
                sql = translate_query(query)
                params_list = []
                for args in args_list:
                    # If arg is a tuple/list, convert to positional map
                    if isinstance(args, (tuple, list)):
                        params_list.append({f"p{i+1}": val for i, val in enumerate(args)})
                    else:
                        params_list.append(args)
                cursor = await self._c.executemany(sql, params_list)
                await self._c.commit()
                return cursor
                
            async def fetch(self, query: str, *args):
                sql = translate_query(query)
                params = {}
                
                # Special handling for ANY($1) array search in SQLite
                if "slug = ANY(:p1)" in sql or "slug = ANY($1)" in sql:
                    slugs = args[0]
                    placeholders = ", ".join([f":s{i}" for i in range(len(slugs))])
                    sql = sql.replace("slug = ANY(:p1)", f"slug IN ({placeholders})")
                    sql = sql.replace("slug = ANY($1)", f"slug IN ({placeholders})")
                    for i, slug in enumerate(slugs):
                        params[f"s{i}"] = slug
                else:
                    params = {f"p{i+1}": val for i, val in enumerate(args)}
                    
                async with self._c.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    await self._c.commit()
                    return [dict(r) for r in rows]
                    
            async def fetchrow(self, query: str, *args):
                sql = translate_query(query)
                params = {f"p{i+1}": val for i, val in enumerate(args)}
                async with self._c.execute(sql, params) as cursor:
                    row = await cursor.fetchone()
                    await self._c.commit()
                    return dict(row) if row else None
                    
            async def fetchval(self, query: str, *args):
                sql = translate_query(query)
                params = {f"p{i+1}": val for i, val in enumerate(args)}
                async with self._c.execute(sql, params) as cursor:
                    row = await cursor.fetchone()
                    await self._c.commit()
                    return row[0] if row else None
                    
        yield SQLiteConnectionWrapper(conn)
        await conn.close()
        
    async def close(self):
        pass


async def get_pool() -> Any:
    """Get or create connection pool (asyncpg Pool or SQLitePoolWrapper)."""
    global _pool
    if _pool is None:
        if IS_SQLITE:
            _pool = SQLitePoolWrapper(DATABASE_URL)
        else:
            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )
    return _pool


async def close_pool():
    """Close connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_db():
    """Initialize database with schema."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if IS_SQLITE:
            # Read and execute SQLite schema
            schema_path = os.path.join(os.path.dirname(__file__), "..", "migrations", "001_initial_schema_sqlite.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = f.read()
                
            # Split by semicolon to run statements sequentially in sqlite
            # We filter out comments and empty statements
            statements = []
            current_stmt = []
            for line in schema.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("--"):
                    continue
                current_stmt.append(line)
                if stripped.endswith(";"):
                    statements.append("\n".join(current_stmt))
                    current_stmt = []
                    
            for stmt in statements:
                try:
                    await conn._c.execute(stmt)
                except Exception as e:
                    print(f"Warning during SQLite schema init statement: {stmt[:50]}... Error: {e}")
            await conn._c.commit()
        else:
            # PostgreSQL schema
            schema_path = os.path.join(os.path.dirname(__file__), "..", "migrations", "001_initial_schema.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = f.read()
            statements = [s.strip() for s in schema.split(";") if s.strip()]
            for stmt in statements:
                if stmt and not stmt.startswith("--"):
                    try:
                        await conn.execute(stmt)
                    except asyncpg.exceptions.DuplicateObjectError:
                        pass
                    except asyncpg.exceptions.UniqueViolationError:
                        pass
                    except Exception as e:
                        print(f"Warning during Postgres schema init: {e}")
                        
    print("[OK] Database initialized")


async def add_domain(domain: str, industry: Optional[str] = None, country: Optional[str] = None) -> int:
    """Add a domain to the database. Returns domain_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # SQLite RETURNING is supported in modern versions, but we fallback just in case
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO domains (domain, industry, country, crawl_status)
                VALUES ($1, $2, $3, 'pending')
                ON CONFLICT (domain) DO UPDATE SET
                    industry = COALESCE(EXCLUDED.industry, domains.industry),
                    country = COALESCE(EXCLUDED.country, domains.country)
                RETURNING id
                """,
                domain, industry, country
            )
            return row["id"]
        except Exception as e:
            # Fallback if RETURNING clause fails or in case of other issues
            if IS_SQLITE:
                # Check if it already exists
                existing = await conn.fetchrow("SELECT id FROM domains WHERE domain = $1", domain)
                if existing:
                    # Update fields
                    await conn.execute(
                        "UPDATE domains SET industry = COALESCE($2, industry), country = COALESCE($3, country) WHERE domain = $1",
                        domain, industry, country
                    )
                    return existing["id"]
                else:
                    # Insert and get last insert rowid
                    cursor = await conn._c.execute(
                        "INSERT INTO domains (domain, industry, country, crawl_status) VALUES (?, ?, ?, 'pending')",
                        (domain, industry, country)
                    )
                    await conn._c.commit()
                    return cursor.lastrowid
            else:
                raise e


async def add_domains_batch(domains: List[Dict[str, Any]]):
    """Add multiple domains at once."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO domains (domain, industry, country, crawl_status)
            VALUES ($1, $2, $3, 'pending')
            ON CONFLICT (domain) DO NOTHING
            """,
            [(d.get("domain"), d.get("industry"), d.get("country")) for d in domains]
        )


async def get_pending_domains(limit: int = 100) -> List[Dict]:
    """Get domains that need crawling."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, domain, last_crawled, fail_count
            FROM domains
            WHERE crawl_status = 'pending'
               OR (crawl_status = 'failed' AND fail_count < 3)
               OR (crawl_status = 'crawled' AND last_crawled < NOW() - INTERVAL '7 days')
            ORDER BY 
                CASE crawl_status 
                    WHEN 'pending' THEN 1 
                    WHEN 'failed' THEN 2 
                    ELSE 3 
                END,
                fail_count ASC,
                last_crawled ASC
            LIMIT $1
            """,
            limit
        )
        return [dict(row) for row in rows]


async def update_domain_crawl_result(
    domain_id: int,
    status: str,
    page_title: Optional[str] = None,
    http_status: Optional[int] = None,
    page_size: Optional[int] = None,
    server_header: Optional[str] = None,
    meta_generator: Optional[str] = None,
    error_message: Optional[str] = None
):
    """Update domain after crawl attempt."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE domains
            SET crawl_status = $2,
                last_crawled = NOW(),
                page_title = COALESCE($3, page_title),
                http_status = $4,
                page_size_bytes = $5,
                server_header = COALESCE($6, server_header),
                meta_generator = COALESCE($7, meta_generator),
                crawl_count = crawl_count + 1,
                fail_count = CASE WHEN $2 = 'failed' THEN fail_count + 1 ELSE fail_count END
            WHERE id = $1
            """,
            domain_id, status, page_title, http_status, page_size, server_header, meta_generator
        )


async def add_tech_detection(
    domain_id: int,
    tech_slug: str,
    confidence: float,
    method: str,
    evidence: str
) -> bool:
    """Add a technology detection. Returns True if added, False if already exists."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get tech_id
        tech_row = await conn.fetchrow(
            "SELECT id FROM technologies WHERE slug = $1",
            tech_slug
        )
        if not tech_row:
            return False

        tech_id = tech_row["id"]

        try:
            await conn.execute(
                """
                INSERT INTO tech_detections (domain_id, tech_id, confidence_score, detection_method, evidence)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (domain_id, tech_id, detection_method) DO UPDATE SET
                    confidence_score = EXCLUDED.confidence_score,
                    evidence = EXCLUDED.evidence,
                    detected_at = NOW()
                """,
                domain_id, tech_id, confidence, method, evidence
            )
            return True
        except Exception as e:
            print(f"Error adding detection: {e}")
            return False


async def add_tech_detections_batch(domain_id: int, detections: List[Dict]):
    """Add multiple detections for a domain."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get all tech slugs to IDs mapping
        slugs = [d["tech_slug"] for d in detections]
        tech_rows = await conn.fetch(
            "SELECT id, slug FROM technologies WHERE slug = ANY($1)",
            slugs
        )
        tech_map = {row["slug"]: row["id"] for row in tech_rows}

        values = []
        for d in detections:
            tech_id = tech_map.get(d["tech_slug"])
            if tech_id:
                values.append((domain_id, tech_id, d["confidence"], d["method"], d["evidence"]))

        if values:
            await conn.executemany(
                """
                INSERT INTO tech_detections (domain_id, tech_id, confidence_score, detection_method, evidence)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (domain_id, tech_id, detection_method) DO UPDATE SET
                    confidence_score = EXCLUDED.confidence_score,
                    evidence = EXCLUDED.evidence,
                    detected_at = NOW()
                """,
                values
            )


async def get_domain_by_id(domain_id: int) -> Optional[Dict]:
    """Get domain details by ID."""
    if IS_SQLITE:
        pool = await get_pool()
        async with pool.acquire() as conn:
            domain_row = await conn.fetchrow(
                "SELECT * FROM domains WHERE id = $1", domain_id
            )
            if not domain_row:
                return None
                
            domain_dict = dict(domain_row)
            
            tech_rows = await conn.fetch(
                """
                SELECT t.name, t.slug, t.category, td.confidence_score as confidence,
                       td.detection_method as method, td.evidence, td.detected_at
                FROM tech_detections td
                JOIN technologies t ON td.tech_id = t.id
                WHERE td.domain_id = $1
                """,
                domain_id
            )
            
            formatted_techs = []
            for row in tech_rows:
                t_dict = dict(row)
                if t_dict.get("detected_at"):
                    t_dict["detected_at"] = str(t_dict["detected_at"])
                formatted_techs.append(t_dict)
                
            domain_dict["technologies"] = formatted_techs
            return domain_dict
    else:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT d.*, 
                       json_agg(json_build_object(
                           'name', t.name,
                           'slug', t.slug,
                           'category', t.category,
                           'confidence', td.confidence_score,
                           'method', td.detection_method,
                           'evidence', td.evidence,
                           'detected_at', td.detected_at
                       )) as technologies
                FROM domains d
                LEFT JOIN tech_detections td ON d.id = td.domain_id
                LEFT JOIN technologies t ON td.tech_id = t.id
                WHERE d.id = $1
                GROUP BY d.id
                """,
                domain_id
            )
            return dict(row) if row else None


async def get_domain_by_name(domain: str) -> Optional[Dict]:
    """Get domain details by domain name."""
    if IS_SQLITE:
        pool = await get_pool()
        async with pool.acquire() as conn:
            domain_row = await conn.fetchrow(
                "SELECT * FROM domains WHERE domain = $1", domain
            )
            if not domain_row:
                return None
                
            domain_dict = dict(domain_row)
            
            tech_rows = await conn.fetch(
                """
                SELECT t.name, t.slug, t.category, td.confidence_score as confidence,
                       td.detection_method as method, td.evidence, td.detected_at
                FROM tech_detections td
                JOIN technologies t ON td.tech_id = t.id
                WHERE td.domain_id = $1
                """,
                domain_dict["id"]
            )
            
            formatted_techs = []
            for row in tech_rows:
                t_dict = dict(row)
                if t_dict.get("detected_at"):
                    t_dict["detected_at"] = str(t_dict["detected_at"])
                formatted_techs.append(t_dict)
                
            domain_dict["technologies"] = formatted_techs
            return domain_dict
    else:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT d.*, 
                       json_agg(json_build_object(
                           'name', t.name,
                           'slug', t.slug,
                           'category', t.category,
                           'confidence', td.confidence_score,
                           'method', td.detection_method,
                           'evidence', td.evidence,
                           'detected_at', td.detected_at
                       )) as technologies
                FROM domains d
                LEFT JOIN tech_detections td ON d.id = td.domain_id
                LEFT JOIN technologies t ON td.tech_id = t.id
                WHERE d.domain = $1
                GROUP BY d.id
                """,
                domain
            )
            return dict(row) if row else None


async def search_domains(query: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    """Search domains by name or title."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.*, 
                   COUNT(td.id) as tech_count
            FROM domains d
            LEFT JOIN tech_detections td ON d.id = td.domain_id
            WHERE d.domain LIKE $1 OR d.page_title LIKE $1
            GROUP BY d.id
            ORDER BY d.last_crawled DESC
            LIMIT $2 OFFSET $3
            """,
            f"%{query}%", limit, offset
        )
        return [dict(row) for row in rows]


async def get_leaderboard(category: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """Get technology leaderboard."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if category:
            rows = await conn.fetch(
                """
                SELECT t.*, COUNT(DISTINCT td.domain_id) as site_count
                FROM technologies t
                LEFT JOIN tech_detections td ON t.id = td.tech_id
                WHERE t.category = $1
                GROUP BY t.id
                ORDER BY site_count DESC
                LIMIT $2
                """,
                category, limit
            )
        else:
            rows = await conn.fetch(
                """
                SELECT t.*, COUNT(DISTINCT td.domain_id) as site_count
                FROM technologies t
                LEFT JOIN tech_detections td ON t.id = td.tech_id
                GROUP BY t.id
                ORDER BY site_count DESC
                LIMIT $1
                """,
                limit
            )
        return [dict(row) for row in rows]


async def get_stats() -> Dict:
    """Get overall statistics."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        total_domains = await conn.fetchval("SELECT COUNT(*) FROM domains")
        crawled_domains = await conn.fetchval("SELECT COUNT(*) FROM domains WHERE crawl_status = 'crawled'")
        failed_domains = await conn.fetchval("SELECT COUNT(*) FROM domains WHERE crawl_status = 'failed'")
        total_detections = await conn.fetchval("SELECT COUNT(*) FROM tech_detections")
        total_technologies = await conn.fetchval("SELECT COUNT(DISTINCT tech_id) FROM tech_detections")

        # Recent activity (24 hours)
        recent_crawls = await conn.fetchval(
            "SELECT COUNT(*) FROM domains WHERE last_crawled > NOW() - INTERVAL '24 hours'"
        )

        # Top categories
        category_stats = await conn.fetch(
            """
            SELECT t.category, COUNT(DISTINCT td.domain_id) as sites, COUNT(*) as detections
            FROM tech_detections td
            JOIN technologies t ON td.tech_id = t.id
            GROUP BY t.category
            ORDER BY sites DESC
            LIMIT 10
            """
        )

        return {
            "total_domains": total_domains,
            "crawled_domains": crawled_domains,
            "failed_domains": failed_domains,
            "pending_domains": total_domains - crawled_domains - failed_domains,
            "total_detections": total_detections,
            "total_technologies": total_technologies,
            "recent_crawls_24h": recent_crawls,
            "crawl_success_rate": round(crawled_domains / max(total_domains, 1) * 100, 2),
            "category_breakdown": [dict(row) for row in category_stats]
        }


async def get_domains_by_tech(tech_slug: str, limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get domains using a specific technology."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.*, td.confidence_score, td.detection_method, td.detected_at
            FROM domains d
            JOIN tech_detections td ON d.id = td.domain_id
            JOIN technologies t ON td.tech_id = t.id
            WHERE t.slug = $1
            ORDER BY td.detected_at DESC
            LIMIT $2 OFFSET $3
            """,
            tech_slug, limit, offset
        )
        return [dict(row) for row in rows]


async def get_cooccurrence(tech_slug1: str, tech_slug2: str) -> Dict:
    """Get co-occurrence stats between two technologies."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            WITH tech1_sites AS (
                SELECT DISTINCT domain_id FROM tech_detections td
                JOIN technologies t ON td.tech_id = t.id
                WHERE t.slug = $1
            ),
            tech2_sites AS (
                SELECT DISTINCT domain_id FROM tech_detections td
                JOIN technologies t ON td.tech_id = t.id
                WHERE t.slug = $2
            ),
            both_sites AS (
                SELECT domain_id FROM tech1_sites
                INTERSECT
                SELECT domain_id FROM tech2_sites
            )
            SELECT 
                (SELECT COUNT(*) FROM tech1_sites) as tech1_count,
                (SELECT COUNT(*) FROM tech2_sites) as tech2_count,
                (SELECT COUNT(*) FROM both_sites) as both_count,
                (SELECT COUNT(*) FROM domains WHERE crawl_status = 'crawled') as total_crawled
            """,
            tech_slug1, tech_slug2
        )

        if result:
            data = dict(result)
            total = max(data["total_crawled"], 1)
            data["tech1_penetration"] = round(data["tech1_count"] / total * 100, 2)
            data["tech2_penetration"] = round(data["tech2_count"] / total * 100, 2)
            data["cooccurrence_rate"] = round(data["both_count"] / max(data["tech1_count"], 1) * 100, 2)
            return data
        return {}


async def get_recent_crawls(limit: int = 20) -> List[Dict]:
    """Get recently crawled domains."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.*, COUNT(td.id) as tech_count
            FROM domains d
            LEFT JOIN tech_detections td ON d.id = td.domain_id
            WHERE d.last_crawled IS NOT NULL
            GROUP BY d.id
            ORDER BY d.last_crawled DESC
            LIMIT $1
            """,
            limit
        )
        return [dict(row) for row in rows]
