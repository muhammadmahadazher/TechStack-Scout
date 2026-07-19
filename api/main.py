"""
TechStack Scout API
FastAPI backend for the web technographics platform.
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.db import (
    get_pool, close_pool, init_db,
    get_stats, get_leaderboard, get_domain_by_id,
    get_domain_by_name, search_domains, get_recent_crawls,
    get_domains_by_tech, get_cooccurrence, add_domain
)


# Pydantic models
class DomainCreate(BaseModel):
    domain: str
    industry: Optional[str] = None
    country: Optional[str] = None


class DomainResponse(BaseModel):
    id: int
    domain: str
    crawl_status: str
    page_title: Optional[str] = None
    last_crawled: Optional[str] = None
    tech_count: Optional[int] = None


class TechnologyResponse(BaseModel):
    id: int
    name: str
    slug: str
    category: str
    site_count: int


class StatsResponse(BaseModel):
    total_domains: int
    crawled_domains: int
    failed_domains: int
    pending_domains: int
    total_detections: int
    total_technologies: int
    recent_crawls_24h: int
    crawl_success_rate: float
    category_breakdown: List[dict]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_pool()


app = FastAPI(
    title="TechStack Scout",
    description="Web technographics intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")


# ============ API ROUTES ============

@app.get("/api/stats", response_model=StatsResponse)
async def api_stats():
    """Get overall platform statistics."""
    return await get_stats()


@app.get("/api/leaderboard")
async def api_leaderboard(
    category: Optional[str] = Query(None, description="Filter by technology category"),
    limit: int = Query(50, ge=1, le=100)
):
    """Get technology adoption leaderboard."""
    return await get_leaderboard(category=category, limit=limit)


@app.get("/api/domains/search")
async def api_search_domains(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Search domains by name or title."""
    return await search_domains(q, limit=limit, offset=offset)


@app.get("/api/domains/recent")
async def api_recent_domains(limit: int = Query(20, ge=1, le=100)):
    """Get recently crawled domains."""
    return await get_recent_crawls(limit=limit)


@app.get("/api/domains/{domain_id}")
async def api_get_domain(domain_id: int):
    """Get detailed information about a specific domain."""
    domain = await get_domain_by_id(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@app.get("/api/domains/by-name/{domain}")
async def api_get_domain_by_name(domain: str):
    """Get domain by its name."""
    result = await get_domain_by_name(domain)
    if not result:
        raise HTTPException(status_code=404, detail="Domain not found")
    return result


@app.get("/api/technologies/{tech_slug}/domains")
async def api_domains_by_tech(
    tech_slug: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get domains using a specific technology."""
    return await get_domains_by_tech(tech_slug, limit=limit, offset=offset)


@app.get("/api/technologies/cooccurrence")
async def api_cooccurrence(
    tech1: str = Query(..., description="First technology slug"),
    tech2: str = Query(..., description="Second technology slug")
):
    """Get co-occurrence statistics between two technologies."""
    return await get_cooccurrence(tech1, tech2)


@app.post("/api/domains")
async def api_add_domain(domain: DomainCreate):
    """Add a new domain to the crawl queue."""
    domain_id = await add_domain(domain.domain, domain.industry, domain.country)
    return {"id": domain_id, "domain": domain.domain, "status": "queued"}


# ============ DASHBOARD ROUTES ============

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard."""
    stats = await get_stats()
    leaderboard = await get_leaderboard(limit=20)
    recent = await get_recent_crawls(limit=10)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "leaderboard": leaderboard,
        "recent": recent,
    })


@app.get("/domain/{domain_id}", response_class=HTMLResponse)
async def domain_detail(domain_id: int, request: Request):
    """Domain detail page."""
    domain = await get_domain_by_id(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    return templates.TemplateResponse("domain.html", {
        "request": request,
        "domain": domain,
    })


@app.get("/technology/{tech_slug}", response_class=HTMLResponse)
async def technology_detail(tech_slug: str, request: Request):
    """Technology detail page."""
    domains = await get_domains_by_tech(tech_slug, limit=50)

    # Get tech info
    from crawler.db import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        tech = await conn.fetchrow(
            "SELECT * FROM technologies WHERE slug = $1",
            tech_slug
        )

    if not tech:
        raise HTTPException(status_code=404, detail="Technology not found")

    return templates.TemplateResponse("technology.html", {
        "request": request,
        "technology": dict(tech),
        "domains": domains,
    })


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: Optional[str] = None):
    """Search results page."""
    results = []
    if q:
        results = await search_domains(q, limit=50)

    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "results": results,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
