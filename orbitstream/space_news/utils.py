# space_news/utils.py
import requests
from bs4 import BeautifulSoup
from readability import Document
import bleach

def fetch_full_html(url: str, timeout: int = 8):
    """Return sanitized HTML for the article body, or None on failure."""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "OrbitStream/1.0"})
        r.raise_for_status()
    except Exception:
        return None

    # Extract the main content area
    html = Document(r.text).summary(html_partial=True)

    # Strip junk and lightly sanitize
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "iframe", "noscript"]):
        tag.decompose()
    for img in soup.find_all("img"):
        img.attrs["loading"] = "lazy"

    return bleach.clean(
        str(soup),
        tags=["p","h2","h3","ul","ol","li","strong","em","blockquote","figure",
              "figcaption","img","a","code","pre","br"],
        attributes={"a": ["href","title","rel","target"], "img": ["src","alt","title","width","height","loading"]},
        protocols=["http","https","data"],
        strip=True
    )
