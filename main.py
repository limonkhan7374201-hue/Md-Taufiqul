"""
NexAudit — AI SEO Audit Backend
FastAPI server with web scraping and AI integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.parse import urlparse
import re
import httpx
from bs4 import BeautifulSoup

# --- App Setup ---
app = FastAPI(title="NexAudit API", version="1.0.0")

# CORS: Allow the frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / Response Models ---
class AuditRequest(BaseModel):
    url: str


class ScrapedData(BaseModel):
    url: str
    title: str | None = None
    description: str | None = None
    h1: str | None = None
    h2_tags: list[str] = []
    h3_tags: list[str] = []
    h4_tags: list[str] = []
    h5_tags: list[str] = []
    h6_tags: list[str] = []
    images_total: int = 0
    images_missing_alt: int = 0
    images_alt_list: list[dict] = []
    canonical: str | None = None
    has_viewport: bool = False
    has_robots: bool = False
    lang_attr: str | None = None
    schema_markup: bool = False
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    h2_count: int = 0
    h3_count: int = 0


# --- Scraper ---
async def scrape_page(url: str) -> ScrapedData:
    """
    Fetch and parse a web page, extracting SEO-relevant metadata.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Meta Description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    description = meta_desc.get("content", "").strip() if meta_desc else None

    # Headings
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else None

    h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3_tags = [h.get_text(strip=True) for h in soup.find_all("h3")]
    h4_tags = [h.get_text(strip=True) for h in soup.find_all("h4")]
    h5_tags = [h.get_text(strip=True) for h in soup.find_all("h5")]
    h6_tags = [h.get_text(strip=True) for h in soup.find_all("h6")]

    # Images
    images = soup.find_all("img")
    images_total = len(images)
    images_missing_alt = 0
    images_alt_list = []
    for img in images:
        alt = img.get("alt", "").strip()
        src = img.get("src", "").strip()
        if not alt:
            images_missing_alt += 1
        images_alt_list.append({"src": src, "alt": alt or None})

    # Canonical
    canonical_tag = soup.find("link", rel="canonical")
    canonical = canonical_tag.get("href", "").strip() if canonical_tag else None

    # Viewport
    viewport_tag = soup.find("meta", attrs={"name": "viewport"})
    has_viewport = viewport_tag is not None

    # Robots
    robots_tag = soup.find("meta", attrs={"name": "robots"})
    has_robots = robots_tag is not None

    # Lang attribute
    html_tag = soup.find("html")
    lang_attr = html_tag.get("lang") if html_tag else None

    # Schema / JSON-LD
    schema_scripts = soup.find_all("script", type="application/ld+json")
    schema_markup = len(schema_scripts) > 0

    # Open Graph
    og_title_tag = soup.find("meta", property="og:title")
    og_title = og_title_tag.get("content", "").strip() if og_title_tag else None

    og_desc_tag = soup.find("meta", property="og:description")
    og_description = og_desc_tag.get("content", "").strip() if og_desc_tag else None

    og_image_tag = soup.find("meta", property="og:image")
    og_image = og_image_tag.get("content", "").strip() if og_image_tag else None

    return ScrapedData(
        url=url,
        title=title,
        description=description,
        h1=h1,
        h2_tags=h2_tags,
        h3_tags=h3_tags,
        h4_tags=h4_tags,
        h5_tags=h5_tags,
        h6_tags=h6_tags,
        images_total=images_total,
        images_missing_alt=images_missing_alt,
        images_alt_list=images_alt_list,
        canonical=canonical,
        has_viewport=has_viewport,
        has_robots=has_robots,
        lang_attr=lang_attr,
        schema_markup=schema_markup,
        og_title=og_title,
        og_description=og_description,
        og_image=og_image,
        h2_count=len(h2_tags),
        h3_count=len(h3_tags),
    )


# --- SEO Issue Detector ---
def detect_issues(data: ScrapedData) -> list[dict]:
    """
    Analyze scraped data and return a list of SEO issues with severity levels.
    """
    issues = []

    # Title checks
    if not data.title:
        issues.append({"severity": "critical", "message": "Missing <title> tag — search engines cannot understand the page topic"})
    elif len(data.title) > 60:
        issues.append({"severity": "warning", "message": f"Title tag is {len(data.title)} characters — exceeds recommended 60-char limit for SERP display"})
    elif len(data.title) < 30:
        issues.append({"severity": "warning", "message": f"Title tag is only {len(data.title)} characters — too short, add more descriptive keywords"})

    # Description checks
    if not data.description:
        issues.append({"severity": "critical", "message": "Missing meta description — Google will auto-generate one, often poorly"})
    elif len(data.description) > 160:
        issues.append({"severity": "warning", "message": f"Meta description is {len(data.description)} characters — exceeds 160-char SERP display limit"})
    elif len(data.description) < 120:
        issues.append({"severity": "info", "message": f"Meta description is {len(data.description)} characters — consider expanding to 150-160 for maximum SERP real estate"})

    # H1 checks
    if not data.h1:
        issues.append({"severity": "critical", "message": "No H1 tag found — the primary heading is essential for both SEO and accessibility"})

    # Image alt text
    if data.images_missing_alt > 0:
        issues.append({"severity": "critical", "message": f"{data.images_missing_alt} of {data.images_total} images missing alt text — impacts accessibility and image search rankings"})

    # Canonical
    if not data.canonical:
        issues.append({"severity": "warning", "message": "No canonical tag — page is vulnerable to duplicate content issues"})

    # Viewport
    if not data.has_viewport:
        issues.append({"severity": "critical", "message": "Missing viewport meta tag — page will not render properly on mobile devices"})

    # Lang attribute
    if not data.lang_attr:
        issues.append({"severity": "warning", "message": "Missing lang attribute on <html> tag — screen readers and search engines may misidentify the language"})

    # Schema markup
    if not data.schema_markup:
        issues.append({"severity": "warning", "message": "No JSON-LD schema markup detected — missing rich snippet opportunities in search results"})

    # Open Graph
    if not data.og_title or not data.og_description:
        issues.append({"severity": "info", "message": "Incomplete Open Graph tags — social media shares will lack custom titles and descriptions"})

    # Positive findings
    if data.canonical:
        issues.append({"severity": "info", "message": "Canonical tag is properly set"})
    if data.has_viewport:
        issues.append({"severity": "info", "message": "Viewport meta tag detected — mobile rendering enabled"})
    if data.schema_markup:
        issues.append({"severity": "info", "message": "Schema markup (JSON-LD) detected on page"})

    return issues


# --- SEO Score Calculator ---
def calculate_score(data: ScrapedData, issues: list[dict]) -> int:
    """
    Calculate an SEO health score from 0-100 based on issues and data quality.
    """
    score = 100
    for issue in issues:
        if issue["severity"] == "critical":
            score -= 12
        elif issue["severity"] == "warning":
            score -= 5
    # Small bonuses
    if data.h1 and len(data.h1) > 10:
        score += 2
    if data.description and 140 <= len(data.description) <= 160:
        score += 3
    if data.schema_markup:
        score += 2
    return max(0, min(100, score))


# --- API Endpoints ---
@app.post("/audit")
async def audit_url(request: AuditRequest):
    """
    Main audit endpoint: scrapes a URL, detects issues, and returns the full analysis.
    Optionally sends data to AI for optimization suggestions (if OPENAI_API_KEY is set).
    """
    # Validate URL format
    try:
        parsed = urlparse(request.url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format. Include scheme (https://).")

    # Scrape the page
    scraped = await scrape_page(request.url)

    # Detect issues
    issues = detect_issues(scraped)

    # Calculate score
    score = calculate_score(scraped, issues)

    # Build base response
    response = {
        "scraped": scraped.model_dump(),
        "issues": issues,
        "score": score,
        "ai_analysis": None,
    }

    # Attempt AI analysis (if API key is configured)
    try:
        from ai_engine import generate_ai_analysis
        ai_result = await generate_ai_analysis(scraped.model_dump(), issues)
        response["ai_analysis"] = ai_result
    except ImportError:
        pass  # AI module not available
    except Exception as e:
        response["ai_analysis_error"] = str(e)

    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "NexAudit API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)