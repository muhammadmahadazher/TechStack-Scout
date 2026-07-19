"""
Generate a fully static version of the TechStack Scout dashboard.
Used for deploying a live-crawled demo directly to GitHub Pages via GitHub Actions.
"""

import os
import sys
import asyncio
import shutil

# Add current folder to path
sys.path.insert(0, os.getcwd())

from crawler.db import get_pool, init_db, get_stats, get_leaderboard, get_recent_crawls, get_domain_by_id, get_domains_by_tech, close_pool
from fastapi.templating import Jinja2Templates

# Create output folder
OUTPUT_DIR = "demo_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "domain"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "technology"), exist_ok=True)


class MockRequest:
    """Mock FastAPI Request object for Jinja2 templates."""
    def __init__(self):
        self.scope = {"type": "http"}


def patch_html_links(html: str, is_subpage=False) -> str:
    """Rewrite absolute backend routes to relative static html file paths for GitHub Pages."""
    prefix = "../" if is_subpage else ""
    
    # Replace absolute navbar and list paths
    html = html.replace('href="/"', f'href="{prefix}index.html"')
    html = html.replace('href="/static/', f'href="{prefix}static/')
    html = html.replace('src="/static/', f'src="{prefix}static/')
    
    # Replace domain paths: href="/domain/12" -> href="domain/12.html" (or ../domain/12.html)
    # Match href="/domain/id" and replace with appropriate prefix
    import re
    html = re.sub(r'href="/domain/(\d+)"', f'href="{prefix}domain/\\1.html"', html)
    
    # Replace technology paths: href="/technology/react" -> href="technology/react.html"
    html = re.sub(r'href="/technology/([\w\-]+)"', f'href="{prefix}technology/\\1.html"', html)
    
    # Replace search paths
    html = html.replace('action="/search"', f'action="{prefix}search.html"')
    
    return html


async def main():
    print("[*] Generating static dashboard for live demo...")
    
    # 1. Initialize DB and read stats
    await init_db()
    
    stats = await get_stats()
    leaderboard = await get_leaderboard(limit=25)
    recent = await get_recent_crawls(limit=15)
    
    # Setup template engine
    templates = Jinja2Templates(directory="web/templates")
    mock_req = MockRequest()
    
    # 2. Render Main Dashboard page
    dashboard_template = templates.get_template("dashboard.html")
    dashboard_html = dashboard_template.render({
        "request": mock_req,
        "stats": stats,
        "leaderboard": leaderboard,
        "recent": recent,
    })
    dashboard_html = patch_html_links(dashboard_html)
    
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(dashboard_html)
    print("    - Generated index.html (Dashboard)")
    
    # 3. Render Search page
    search_template = templates.get_template("search.html")
    search_html = search_template.render({
        "request": mock_req,
        "query": None,
        "results": [],
    })
    search_html = patch_html_links(search_html)
    with open(os.path.join(OUTPUT_DIR, "search.html"), "w", encoding="utf-8") as f:
        f.write(search_html)
    print("    - Generated search.html")
    
    # 4. Render individual Domain detail pages for crawled domains
    domain_template = templates.get_template("domain.html")
    pool = await get_pool()
    async with pool.acquire() as conn:
        crawled_domains = await conn.fetch("SELECT id, domain FROM domains WHERE crawl_status = 'crawled'")
        for d_row in crawled_domains:
            d_id = d_row["id"]
            domain_detail = await get_domain_by_id(d_id)
            
            d_html = domain_template.render({
                "request": mock_req,
                "domain": domain_detail,
            })
            d_html = patch_html_links(d_html, is_subpage=True)
            
            with open(os.path.join(OUTPUT_DIR, "domain", f"{d_id}.html"), "w", encoding="utf-8") as f:
                f.write(d_html)
        print(f"    - Generated {len(crawled_domains)} static domain pages")
        
        # 5. Render individual Technology detail pages
        tech_template = templates.get_template("technology.html")
        tech_rows = await conn.fetch("SELECT * FROM technologies")
        for t_row in tech_rows:
            slug = t_row["slug"]
            tech_domains = await get_domains_by_tech(slug, limit=50)
            
            t_html = tech_template.render({
                "request": mock_req,
                "technology": dict(t_row),
                "domains": tech_domains,
            })
            t_html = patch_html_links(t_html, is_subpage=True)
            
            with open(os.path.join(OUTPUT_DIR, "technology", f"{slug}.html"), "w", encoding="utf-8") as f:
                f.write(t_html)
        print(f"    - Generated {len(tech_rows)} static technology catalog pages")
        
    # 6. Copy static assets (CSS) to output folder
    static_dest = os.path.join(OUTPUT_DIR, "static")
    if os.path.exists(static_dest):
        shutil.rmtree(static_dest)
    shutil.copytree("web/static", static_dest)
    print("    - Copied static assets")
    
    await close_pool()
    print("[*] Static demo site generation complete in folder: demo_output")


if __name__ == "__main__":
    asyncio.run(main())
