import os
import logging
from typing import List, Optional, Dict
import requests
from tqdm import tqdm
from litrev.models import SearchConfig, Paper
from litrev.utils import robust_search

# Mapping from user-friendly names to Scopus Subject Area Codes
# See https://dev.elsevier.com/subject_areas.html
MACRO_AREA_MAP = {
    "computer science": "COMP",
    "physics": "PHYS",
    "mathematics": "MATH",
    "engineering": "ENGI",
    "medicine": "MEDI",
    "neuroscience": "NEUR",
    "social sciences": "SOCI",
}

@robust_search()
def search_scopus(config: SearchConfig, query_log: Optional[Dict[str, str]] = None) -> List[Paper]:
    """Searches the Scopus API using a structured AND of ORs query."""
    log = logging.getLogger(__name__)
    
    # --- API Key Check ---
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        log.error("SCOPUS_API_KEY environment variable not set. Skipping Scopus search.")
        return []

    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json"
    }
    base_url = "https://api.elsevier.com/content/search/scopus"
    
    query_clauses = []

    # --- Query Construction (Scopus Syntax) ---
    if config.inclusion_keywords:
        # TITLE-ABS-KEY searches in Title, Abstract, and Keywords
        keyword_part = " OR ".join(config.inclusion_keywords)
        query_clauses.append(f"TITLE-ABS-KEY({keyword_part})")

    if config.authors:
        # AUTH() searches for author names
        author_part = " OR ".join([f'"{a}"' for a in config.authors])
        query_clauses.append(f"AUTH({author_part})")
        
    if config.venues:
        # SRCTITLE() searches for the journal/conference name
        venue_part = " OR ".join([f'"{v}"' for v in config.venues])
        query_clauses.append(f"SRCTITLE({venue_part})")
        
    if config.macro_areas:
        area_codes = [MACRO_AREA_MAP.get(area.lower(), area) for area in config.macro_areas]
        area_part = " OR ".join(area_codes)
        query_clauses.append(f"SUBJAREA({area_part})")

    if not query_clauses:
        log.warning("Scopus search requires keywords, authors, venues, or macro areas.")
        return []

    # --- Final Query and API Call ---
    query = " AND ".join(query_clauses)
    log.info(f"Constructed Scopus query: {query}")
    
    if query_log is not None:
        query_log["Scopus"] = query
    
    params = {
        "query": query,
        "count": config.max_results,
        "view": "COMPLETE" # Required to get the abstract
    }

    try:
        data = requests.get(base_url, params=params, headers=headers)
    except Exception as e:
        log.error(f"Scopus search failed after retries: {e}")
        return []

    entries = data.get("search-results", {}).get("entry", [])
    if not entries:
        return []
        
    results = []
    for item in tqdm(entries, desc="Processing Scopus results"):
        # --- Data Mapping ---
        paper_year_str = item.get("prism:coverDate", "")[:4]
        if not paper_year_str.isdigit(): continue
        paper_year = int(paper_year_str)

        if config.years:
            if isinstance(config.years, int) and paper_year != config.years: continue
            if isinstance(config.years, tuple) and not (config.years[0] <= paper_year <= config.years[1]): continue
        
        title = item.get("dc:title", "No Title")
        abstract = item.get("dc:description", "")
        full_text_lower = (title + " " + abstract).lower()
        if config.exclusion_keywords and any(ex_k.lower() in full_text_lower for ex_k in config.exclusion_keywords): continue
        
        authors = [author.get("authname", "") for author in item.get("author", [])]
        venue = item.get("prism:publicationName", "")
        # Find the main link to the paper
        url = next((link['@href'] for link in item.get('link', []) if link.get('@ref') == 'scopus'), None)

        results.append(Paper(
            title=title, authors=authors, year=paper_year,
            venue=venue, url=url, summary=abstract, source="Scopus"
        ))
        
    return results

