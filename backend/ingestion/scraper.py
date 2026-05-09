import asyncio
import re
import time
import requests
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


BASE_URL = "https://overwatch.fandom.com/wiki"
DEFAULT_HEROES = [
    "Ana", "Ashe", "Baptiste", "Bastion", "Brigitte", "Cassidy", "D.Va", "Doomfist",
    "Echo", "Genji", "Hanzo", "Illari", "Junker Queen", "Junkrat", "Kiriko", "Lifeweaver",
    "Lucio", "Mauga", "Mei", "Mercy", "Moira", "Orisa", "Pharah", "Ramattra", "Reaper",
    "Reinhardt", "Roadhog", "Sigma", "Sojourn", "Soldier: 76", "Sombra", "Symmetra",
    "Torbjorn", "Tracer", "Venture", "Widowmaker", "Winston", "Wrecking Ball", "Zarya",
    "Zenyatta"
]


@dataclass
class ScrapedDocument:
    title: str
    text: str
    hero: str | None
    category: str
    date: str | None
    url: str


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _category_from_heading(heading: str) -> str:
    lowered = heading.lower()
    if "ability" in lowered:
        return "ability"
    if "story" in lowered or "lore" in lowered or "biography" in lowered:
        return "lore"
    if "patch" in lowered or "change" in lowered:
        return "patch"
    return "stats"


def _heading_level(node) -> int:
    if node.name and re.fullmatch(r"h[1-6]", node.name):
        return int(node.name[1])
    return 7


def _table_text(table) -> str:
    rows: list[str] = []
    for row in table.select("tr"):
        cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in row.select("th,td")]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 2:
            rows.append(f"{cells[0]}: {' '.join(cells[1:])}")
        elif cells:
            rows.append(cells[0])
    return ". ".join(rows)


def _section_text(start_node) -> str:
    level = _heading_level(start_node)
    parts: list[str] = []
    for sibling in start_node.find_next_siblings():
        if sibling.name and re.fullmatch(r"h[1-6]", sibling.name) and _heading_level(sibling) <= level:
            break
        if sibling.name == "table":
            text = _table_text(sibling)
        else:
            for noisy in sibling.select(".reference, .mw-editsection, script, style"):
                noisy.decompose()
            text = _clean_text(sibling.get_text(" ", strip=True))
        if text:
            parts.append(text)
    return _clean_text(" ".join(parts))


def _extract_ability_docs(soup, hero: str, url: str) -> list[ScrapedDocument]:
    docs: list[ScrapedDocument] = []
    for heading in soup.select("h3, h4"):
        title = _clean_text(heading.get_text(" ", strip=True)).replace("[edit]", "")
        if not title or title.lower() in {"passive abilities", "weapons", "abilities"}:
            continue
        text = _section_text(heading)
        lowered = text.lower()
        looks_like_ability = any(
            marker in lowered
            for marker in ["damage:", "healing:", "cooldown:", "ammo:", "rate of fire:", "duration:", "projectile speed:", "secondary fire", "primary fire"]
        )
        if looks_like_ability and len(text) > 80:
            docs.append(
                ScrapedDocument(
                    title=f"{hero} - {title}",
                    text=f"{title}. {text}",
                    hero=hero,
                    category="ability",
                    date=None,
                    url=f"{url}#{title.replace(' ', '_')}",
                )
            )
    return docs


def _extract_balance_docs(soup, hero: str, url: str) -> list[ScrapedDocument]:
    docs: list[ScrapedDocument] = []
    for heading in soup.select("h2, h3"):
        title = _clean_text(heading.get_text(" ", strip=True)).replace("[edit]", "")
        if "balance" not in title.lower() and "patch" not in title.lower():
            continue
        text = _section_text(heading)
        if len(text) > 120:
            docs.append(
                ScrapedDocument(
                    title=f"{hero} - {title}",
                    text=text,
                    hero=hero,
                    category="patch",
                    date=None,
                    url=f"{url}#{title.replace(' ', '_')}",
                )
            )
    return docs


def _parse_hero_page(html: str, hero: str, url: str) -> list[ScrapedDocument]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".mw-parser-output")
    if not content:
        return []

    docs: list[ScrapedDocument] = []
    docs.extend(_extract_ability_docs(soup, hero, url))
    docs.extend(_extract_balance_docs(soup, hero, url))
    current_heading = f"{hero} overview"
    current_category = "stats"
    current_parts: list[str] = []

    def flush() -> None:
        text = _clean_text(" ".join(current_parts))
        if len(text) > 120:
            docs.append(
                ScrapedDocument(
                    title=current_heading,
                    text=text,
                    hero=hero,
                    category=current_category,
                    date=None,
                    url=url,
                )
            )

    for node in content.find_all(["h2", "h3", "p", "li"]):
        if node.name in {"h2", "h3"}:
            flush()
            current_heading = _clean_text(node.get_text(" ", strip=True)).replace("[edit]", "")
            current_category = _category_from_heading(current_heading)
            current_parts = []
        else:
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                current_parts.append(text)
    flush()
    return docs


async def scrape_hero(scraper, hero: str, max_retries: int = 3) -> list[ScrapedDocument]:
    """Scrape a hero page with retry logic and exponential backoff using cloudscraper."""
    slug = hero.replace(" ", "_")
    url = f"{BASE_URL}/{slug}"
    
    for attempt in range(max_retries):
        try:
            # Add delay between requests to avoid rate limiting
            if attempt > 0:
                await asyncio.sleep(1)
            
            # Use cloudscraper to bypass Cloudflare
            response = scraper.get(url, timeout=20)
            response.raise_for_status()
            return _parse_hero_page(response.text, hero, url)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                print(f"Scrape attempt {attempt + 1} failed for {hero}: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"Failed to scrape {hero} after {max_retries} attempts: {e}")
                raise
    return []


async def scrape_heroes(heroes: Iterable[str] = DEFAULT_HEROES) -> list[ScrapedDocument]:
    """Scrape multiple heroes using cloudscraper to bypass Cloudflare."""
    import cloudscraper
    
    # Create a cloudscraper instance that automatically handles Cloudflare
    scraper = cloudscraper.create_scraper()
    
    docs: list[ScrapedDocument] = []
    hero_list = list(heroes)
    
    for idx, hero in enumerate(hero_list):
        try:
            # Add delay between requests to avoid rate limiting
            if idx > 0:
                await asyncio.sleep(2)
            
            print(f"Scraping {hero} ({idx + 1}/{len(hero_list)})...")
            batch = await scrape_hero(scraper, hero, max_retries=3)
            docs.extend(batch)
            print(f"Successfully scraped {len(batch)} documents for {hero}")
        except Exception as e:
            print(f"Error scraping {hero}: {e}")
            continue
    
    return docs


def dated_patch_doc(title: str, text: str, url: str, date: datetime | None = None) -> ScrapedDocument:
    return ScrapedDocument(
        title=title,
        text=text,
        hero=None,
        category="patch",
        date=(date or datetime.utcnow()).date().isoformat(),
        url=url,
    )
