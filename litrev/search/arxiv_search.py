import logging
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from tqdm import tqdm
from litrev.models import SearchConfig, Paper
from litrev.utils import robust_search

# ArXiv API base URL as per documentation
ARXIV_API_URL = "http://export.arxiv.org/api/query"

# Mapping from user-friendly names to arXiv categories
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

def _get_text(element, tag, namespaces, default=""):
    """Helper to safely get text from an XML element."""
    found = element.find(tag, namespaces)
    return found.text.strip() if found is not None and found.text else default

@robust_search()
def search_arxiv(config: SearchConfig, query_log: Optional[Dict[str, str]] = None) -> List[Paper]:
    """
    Searches the ArXiv API directly using the documented advanced query syntax
    and parses the XML response.
    """
    log = logging.getLogger(__name__)
    query_clauses = []

    # --- 1. CONSTRUCT ADVANCED QUERY STRING AS PER DOCUMENTATION ---

    # Clause 1: Inclusion Keywords - ( (k1a AND k1b) OR (k2a AND k2b) )
    if config.inclusion_keywords:
        group_clauses = []
        for group in config.inclusion_keywords:
            print(group)
            # Each term is prefixed with "all:", and terms are joined with " AND "
            terms_in_group = [term.strip() for term in group.split(",")]
            and_terms = " AND ".join([f'all:"{term}"' for term in terms_in_group])
            #and_terms = "all:"+",".join([f'"{term}"' for term in terms_in_group])
            group_clauses.append(f"({and_terms})")
        keyword_part = " OR ".join(group_clauses)
        query_clauses.append(f"({keyword_part})")
    
    exclusion_part = ""
    if config.exclusion_keywords:
        # Exclusion keywords are OR'd together and prefixed with NOT
        exclusion_part = " OR ".join([f'all:{term.strip()}' for term in config.exclusion_keywords])

    # Clause 2: Authors (OR'd)
    if config.authors:
        author_part = " OR ".join([f'au:"{a}"' for a in config.authors])
        query_clauses.append(f"({author_part})")

    # Clause 3: Macro Areas (OR'd)
    if config.macro_areas:
        cat_parts = [f"cat:{MACRO_AREA_MAP.get(area.lower(), area)}" for area in config.macro_areas]
        category_part = " OR ".join(cat_parts)
        query_clauses.append(f"({category_part})")
    
    if not query_clauses:
        log.warning("ArXiv search requires keywords, authors, or macro areas.")
        return []

    # Final Query: Join all top-level clauses with " AND "
    query = " AND ".join(query_clauses) + (" ANDNOT "+ exclusion_part if exclusion_part else "")
    log.info(f"Constructed ArXiv API query: {query}")
    print(query)
    if query_log is not None:
        query_log["ArXiv"] = query

    # --- 2. MAKE API CALL, RESPECTING LIMITS ---
    
    # The API has a hard limit of 2000 results per request.
    results_to_fetch = min(config.max_results, 2000)
    if config.max_results > 2000:
        log.warning(f"User requested {config.max_results} results, but ArXiv API is limited to 2000 per query. Fetching 2000.")

    params = {
        'search_query': query,
        'max_results': results_to_fetch,
        'sortBy': 'lastUpdatedDate',
        'sortOrder': 'descending'
    }
    
    response = requests.get(ARXIV_API_URL, params=params)
    print(response.url)
    response.raise_for_status()

    # --- 3. PARSE XML RESPONSE ---
    try:
        root = ET.fromstring(response.content)
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', namespaces)
    except ET.ParseError as e:
        log.error(f"Failed to parse ArXiv XML response: {e}")
        return []

    results = []
    for entry in tqdm(entries, desc="Processing ArXiv results"):
        title = _get_text(entry, 'atom:title', namespaces).replace('\n', ' ').strip()
        summary = _get_text(entry, 'atom:summary', namespaces).replace('\n', ' ')
        
        published_date = _get_text(entry, 'atom:published', namespaces)
        paper_year = int(published_date.split('-')[0]) if published_date else None
        
        # Client-side filtering for year range and exclusion keywords
        if paper_year and config.years:
            if isinstance(config.years, int) and paper_year != config.years: continue
            if isinstance(config.years, tuple) and not (config.years[0] <= paper_year <= config.years[1]): continue
        
        full_text_lower = (title + ' ' + summary).lower()
        if config.exclusion_keywords and any(ex_k.lower() in full_text_lower for ex_k in config.exclusion_keywords): continue
        
        authors = [author.find('atom:name', namespaces).text for author in entry.findall('atom:author', namespaces)]
        
        pdf_link = ""
        for link in entry.findall('atom:link', namespaces):
            if link.get('title') == 'pdf':
                pdf_link = link.get('href')
                break
        
        results.append(Paper(
            title=title, authors=authors, year=paper_year,
            url=pdf_link, summary=summary, source="ArXiv"
        ))

    return results