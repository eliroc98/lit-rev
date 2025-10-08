import logging
from typing import List
from litrev.models import SearchConfig, Paper
from litrev.search import acl_search, arxiv_search, dblp_search, scholar_search, scopus_search

# A list of all available search functions
SEARCH_SOURCES = [
    {"name": "ACL Anthology", "func": acl_search.search_acl},
    {"name": "ArXiv", "func": arxiv_search.search_arxiv},
    {"name": "DBLP", "func": dblp_search.search_dblp},
    {"name": "Scopus", "func": scopus_search.search_scopus},
    {"name": "Google Scholar", "func": scholar_search.search_scholar},
]

def run_search_pipeline(config: SearchConfig, progress_callback=None) -> List[Paper]:
    """
    Takes a SearchConfig object and executes the search across all sources.
    This is the core, reusable logic for any UI (CLI, Web, etc.).
    """
    all_papers: List[Paper] = []
    log = logging.getLogger(__name__)
    log.info(f"Starting search pipeline with config: {config.model_dump_json(exclude_unset=True)}")

    for i, source in enumerate(SEARCH_SOURCES):
        name = source["name"]
        func = source["func"]
        log.info(f"--- Searching {name}... ---")
        
        # Update progress if a callback is provided (for Streamlit)
        if progress_callback:
            progress_callback(i / len(SEARCH_SOURCES), f"Searching {name}...")
        
        try:
            results = func(config)
            all_papers.extend(results)
            log.info(f"Found {len(results)} papers from {name}.")
        except Exception as e:
            log.error(f"Failed to search {name}: {e}")
            
    # Final progress update
    if progress_callback:
        progress_callback(1.0, "Processing final results...")

    # De-duplicate results based on URL or title
    unique_papers = list({(p.url or p.title.lower()): p for p in all_papers}.values())
    log.info(f"Total unique papers found: {len(unique_papers)}")
    
    return unique_papers