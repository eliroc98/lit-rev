import logging
from typing import List, Optional, Dict
import requests
import json
from tqdm import tqdm
from litrev.models import SearchConfig, Paper
from litrev.utils import robust_search

@robust_search()
def search_dblp(config: SearchConfig, query_log: Optional[Dict[str, str]] = None) -> List[Paper]:
    """
    Searches DBLP using a structured "AND of ORs" query, mirroring the ArXiv logic.
    """
    log = logging.getLogger(__name__)
    query_clauses = []

    # Clause 1: Inclusion Keywords - ((k1a k1b)|(k2a k2b))
    if config.inclusion_keywords:
        group_clauses = []
        for group in config.inclusion_keywords:
            # Join the terms within a group with spaces (AND)
            and_terms = " ".join([f'"{term}"' for term in group])
            group_clauses.append(f"({and_terms})")
        # Join the AND-groups with a pipe (OR)
        keyword_part = "|".join(group_clauses)
        query_clauses.append(f"({keyword_part})")

    # Clause 2: Authors (OR'd)
    if config.authors:
        author_part = "|".join([f'author:"{a}"' for a in config.authors])
        query_clauses.append(f"({author_part})")

    # Clause 3: Venues (OR'd)
    if config.venues:
        venue_part = "|".join([f'venue:"{v}"' for v in config.venues])
        query_clauses.append(f"({venue_part})")

    if not query_clauses:
        log.warning("DBLP search requires keywords, authors, or venues.")
        return []

    # Final Query: Join clauses with space (DBLP's AND)
    query = " ".join(query_clauses)
    log.info(f"Constructed DBLP API query: {query}")
    if query_log is not None:
        query_log["DBLP"] = query

    params = {"q": query, "format": "json", "h": config.max_results}
    
    # --- 3. EXECUTE THE FINAL, ROBUST REQUEST ---
    try:
        data = requests.get("https://dblp.org/search/publ/api", params=params)
    except Exception as e:
        log.error(f"Final DBLP search failed after retries: {e}")
        return []
    data = json.loads(data.text.replace("\\r\\n", ""))
    hits = data.get("result", {}).get("hits", {}).get("hit", [])
    if not hits:
        return []

    # --- 4. PROCESS THE RESULTS ---
    results = []
    for item in tqdm(hits, desc="Processing DBLP results"):
        info = item.get("info", {})
        year_val = info.get("year")
        paper_year = None
        if isinstance(year_val, list):
            paper_year = int(year_val[0]) if year_val and year_val[0].isdigit() else None
        elif isinstance(year_val, str) and year_val.isdigit():
            paper_year = int(year_val)

        if paper_year and config.years:
            if isinstance(config.years, int) and paper_year != config.years: 
                continue
            if isinstance(config.years, tuple) and not (config.years[0] <= paper_year <= config.years[1]): 
                continue
        
        title_lower = info.get('title', '').lower()
        if config.exclusion_keywords and any(ex_k.lower() in title_lower for ex_k in config.exclusion_keywords): 
            continue
        
        authors_data = info.get('authors', {}).get('author', [])
        authors = [a.get('text', '') for a in ([authors_data] if isinstance(authors_data, dict) else authors_data)]
        
        results.append(Paper(
            title=info.get('title', 'No Title'), authors=authors, year=paper_year,
            venue=info.get('venue'), url=info.get('ee'), source="DBLP"
        ))

    return results