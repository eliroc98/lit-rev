import os
import logging
from typing import List, Optional, Dict
import json
import requests
from tqdm import tqdm
from litrev.models import SearchConfig, Paper
from litrev.utils import robust_search, extract_year

@robust_search()
def search_scholar(config: SearchConfig, query_log: Optional[Dict[str, str]] = None) -> List[Paper]:
    """Searches Google Scholar via SerpApi using a structured AND of ORs query."""
    log = logging.getLogger(__name__)
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not set.")

    query_clauses = []

    # Clause 1: Inclusion Keywords - (("k1a" "k1b") OR ("k2a" "k2b"))
    if config.inclusion_keywords:
        group_clauses = []
        for group in config.inclusion_keywords:
            # Google's AND is a space. Quotes are for phrases.
            and_terms = " ".join([f'"{term}"' for term in group])
            group_clauses.append(f"({and_terms})")
        keyword_part = " OR ".join(group_clauses)
        query_clauses.append(f"({keyword_part})")

    # Other clauses are simple ORs
    if config.authors:
        query_clauses.append(f"({' OR '.join(config.authors)})")
    if config.venues:
        query_clauses.append(f"({' OR '.join(config.venues)})")
    if config.macro_areas:
        query_clauses.append(f"({' OR '.join(config.macro_areas)})")

    if not query_clauses:
        log.warning("Google Scholar search requires criteria.")
        return []

    # Final Query: Join clauses with space (Google's AND)
    query = " ".join(query_clauses)
    log.info(f"Constructed Google Scholar (SerpApi) query: {query}")
    if query_log is not None:
        query_log["Google Scholar (SerpApi)"] = query
        
    # --- 3. PAGINATION AND API CALLS ---
    all_results = []
    offset = 0
    num_per_page = 20
    
    # Use tqdm for the overall progress towards the user's max_results goal
    with tqdm(total=config.max_results, desc="Fetching Scholar results") as pbar:
        while len(all_results) < config.max_results:
            params = {
                "engine": "google_scholar",
                "api_key": api_key,
                "q": query,
                "num": num_per_page,
                "start": offset,
            }

            # Add year filtering to the API parameters
            if config.years:
                if isinstance(config.years, int):
                    params["as_ylo"] = params["as_yhi"] = config.years
                elif isinstance(config.years, tuple):
                    params["as_ylo"], params["as_yhi"] = config.years

            search = requests.get("https://serpapi.com/search?engine=google_scholar", params)
            data = json.loads(search.text)
            
            organic_results = data.get("organic_results", [])
            if not organic_results:
                break # No more results found

            for item in organic_results:
                # --- 4. DATA MAPPING AND FILTERING ---
                title = item.get('title', 'No Title')
                pub_info = item.get('publication_info', {})
                abstract = item.get('snippet', '')

                full_text_lower = (title + " " + abstract).lower()
                if config.exclusion_keywords and any(ex_k.lower() in full_text_lower for ex_k in config.exclusion_keywords): 
                    continue
                
                paper_obj = Paper(
                    title=title,
                    authors=[author.get('name', '') for author in pub_info.get('authors', [])],
                    year=extract_year(pub_info.get('summary', '')),
                    venue=None,
                    url=item.get('link'),
                    summary=abstract,
                    source="Google Scholar (SerpApi)"
                )
                all_results.append(paper_obj)
                pbar.update(1) # Increment progress bar for each paper processed
                
                if len(all_results) >= config.max_results:
                    break

            offset += num_per_page

    return all_results[:config.max_results]