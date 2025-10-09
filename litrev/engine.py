import logging
from typing import List, Tuple, Dict
from litrev.models import SearchConfig, Paper
from litrev.search import acl_search, arxiv_search, dblp_search, scholar_search, scopus_search

SEARCH_SOURCES = [
    {"name": "ACL Anthology", "func": acl_search.search_acl},
    {"name": "ArXiv", "func": arxiv_search.search_arxiv},
    {"name": "DBLP", "func": dblp_search.search_dblp},
    {"name": "Scopus", "func": scopus_search.search_scopus},
    {"name": "Google Scholar (SerpApi)", "func": scholar_search.search_scholar},
]

def run_search_pipeline(config: SearchConfig, progress_callback=None) -> Tuple[List[Paper], List[str], Dict[str, str]]:
    """
    Executes the search across all sources.
    Returns a tuple containing: (a list of ALL papers including duplicates, errors, a log of final queries).
    """
    all_papers: List[Paper] = []
    errors: List[str] = []
    query_log: Dict[str, str] = {}
    log = logging.getLogger(__name__)
    log.info(f"Starting search pipeline with config: {config.model_dump_json(exclude_unset=True)}")
    if config.sources_to_search:
        sources_to_run = [s for s in SEARCH_SOURCES if s["name"] in config.sources_to_search]
    else:
        sources_to_run = SEARCH_SOURCES

    for i, source in enumerate(sources_to_run):
        name = source["name"]
        func = source["func"]
        log.info(f"--- Searching {name}... ---")
        if progress_callback:
            progress_callback(i / len(sources_to_run), f"Searching {name}...")
        try:
            results = func(config, query_log=query_log)
            all_papers.extend(results)
            log.info(f"Found {len(results)} papers from {name}.")
        except Exception as e:
            error_message = f"Failed to search {name}: {e}"
            log.error(error_message)
            errors.append(error_message)
            
    if progress_callback:
        progress_callback(1.0, "Processing final results...")

    log.info(f"Total papers found (with duplicates): {len(all_papers)}")
    
    return all_papers, errors, query_log