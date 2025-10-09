import logging
import arxiv
from typing import List, Optional, Dict
from tqdm import tqdm
from litrev.models import SearchConfig, Paper
from litrev.utils import robust_search

# Mapping from user-friendly names to arXiv categories (can be expanded)
MACRO_AREA_MAP = {
    "computer science": "cs.*",
    "physics": "physics.*",
    "mathematics": "math.*",
    "quantitative biology": "q-bio.*",
    "quantitative finance": "q-fin.*",
    "statistics": "stat.*",
    "electrical engineering": "eess.*",
    "economics": "econ.*",
}

@robust_search()
def search_arxiv(config: SearchConfig, query_log: Optional[Dict[str, str]] = None) -> List[Paper]:
    """Searches arXiv using a structured AND of ORs query."""
    log = logging.getLogger(__name__)
    query_clauses = []

    # Clause 1: (keyword1 OR keyword2 OR ...)
    if config.inclusion_keywords:
        keyword_part = " OR ".join([f'all:"{k}"' for k in config.inclusion_keywords])
        query_clauses.append(f"({keyword_part})")

    # Clause 2: (author1 OR author2 OR ...)
    if config.authors:
        author_part = " OR ".join([f'au:"{a}"' for a in config.authors])
        query_clauses.append(f"({author_part})")

    # Clause 3: (category1 OR category2 OR ...)
    if config.macro_areas:
        cat_parts = []
        for area in config.macro_areas:
            cat_parts.append(f"cat:{MACRO_AREA_MAP.get(area.lower(), area)}")
        category_part = " OR ".join(cat_parts)
        query_clauses.append(f"({category_part})")
    
    if not query_clauses:
        log.warning("arXiv search requires keywords, authors, or macro areas.")
        return []

    # Final Query: (Clause 1) AND (Clause 2) AND (Clause 3)
    query = " AND ".join(query_clauses)
    log.info(f"Constructed arXiv query: {query}")
    if query_log is not None:
        query_log["ArXiv"] = query

    search = arxiv.Search(query=query, max_results=config.max_results)
    
    results = []
    for result in tqdm(search.results(), desc="Fetching arXiv results"):
        paper_year = result.published.year
        if config.years:
            if isinstance(config.years, int) and paper_year != config.years: continue
            if isinstance(config.years, tuple) and not (config.years[0] <= paper_year <= config.years[1]): continue
        
        full_text_lower = (result.title + ' ' + result.summary).lower()
        if config.exclusion_keywords and any(ex_k.lower() in full_text_lower for ex_k in config.exclusion_keywords): continue
        
        results.append(Paper(
            title=result.title, authors=[author.name for author in result.authors],
            year=paper_year, url=result.pdf_url, summary=result.summary, source="arXiv"
        ))

    return results