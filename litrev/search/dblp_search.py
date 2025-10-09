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
    Searches DBLP using a correctly structured "AND of ORs" query.
    This version correctly looks up author and venue names for precise querying.
    """
    log = logging.getLogger(__name__)
    query_clauses = []

    # --- 1. CONSTRUCT QUERY CLAUSES FOR EACH CATEGORY ---

    # Clause 1: Keywords (simple OR)
    if config.inclusion_keywords:
        keyword_part = "|".join(config.inclusion_keywords)
        query_clauses.append(f"{keyword_part}")
    
    # Clause 2: Authors (requires lookups)
    if config.authors:
        formatted_authors = []
        log.info("Looking up DBLP author names...")
        for author in tqdm(config.authors, desc="Querying Authors"):
            params = {"q": author, "format": "json", "h": 1}
            try:
                data = requests.get("https://dblp.org/search/author/api", params=params)
                data = json.loads(data.text.replace("\\r\\n", ""))
                # Check for a valid, non-empty hit list
                if data and data.get('result', {}).get('hits', {}).get('hit'):
                    # Format: author:Firstname_Lastname:
                    dblp_name = data['result']['hits']['hit'][0]['info']['author'].replace(" ", "_")
                    formatted_authors.append(f"author:{dblp_name}:")
                else:
                    log.warning(f"Could not find a DBLP author match for '{author}'. Skipping.")
            except Exception as e:
                log.error(f"Failed to look up author '{author}': {e}. Skipping.")
        
        if formatted_authors:
            author_part = "|".join(formatted_authors)
            query_clauses.append(f"{author_part}")

    # Clause 3: Venues (requires lookups)
    if config.venues:
        formatted_venues = []
        log.info("Looking up DBLP venue acronyms...")
        for venue in tqdm(config.venues, desc="Querying Venues"):
            params = {"q": venue, "format": "json", "h": 1}
            try:
                data = requests.get("https://dblp.org/search/venue/api", params=params)
                data = json.loads(data.text.replace("\\r\\n", ""))
                if data and data.get('result', {}).get('hits', {}).get('hit'):
                    # Format: streamid:conf/ACRONYM:
                    acronym = data['result']['hits']['hit'][0]['info']['acronym'].lower()
                    formatted_venues.append(f"streamid:conf/{acronym}:")
                else:
                    log.warning(f"Could not find a DBLP venue match for '{venue}'. Skipping.")
            except Exception as e:
                log.error(f"Failed to look up venue '{venue}': {e}. Skipping.")
        
        if formatted_venues:
            venue_part = "|".join(formatted_venues)
            query_clauses.append(f"{venue_part}")

    if not query_clauses:
        log.warning("DBLP search requires keywords, authors, or venues, and at least one must be valid.")
        return []

    # --- 2. COMBINE CLAUSES WITH SPACES (DBLP's AND OPERATOR) ---
    query = " ".join(query_clauses)
    log.info(f"Constructed final DBLP query: {query}")
    
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
        paper_year = int(info["year"]) if info.get("year") else None

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