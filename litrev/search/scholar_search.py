import logging
from typing import List
from itertools import islice
from scholarly import scholarly, ProxyGenerator
from tqdm import tqdm
from litrev.models import SearchConfig, Paper
from litrev.utils import robust_search

@robust_search()
def search_scholar(config: SearchConfig) -> List[Paper]:
    """Searches Google Scholar with a relevance ranking system."""
    log = logging.getLogger(__name__)
    pg = ProxyGenerator()
    if pg.FreeProxies():
        scholarly.use_proxy(pg)
        log.info("Successfully configured scholarly to use free proxies.")
    else:
        log.warning("Could not fetch free proxies. Proceeding with direct connection.")

    query_clauses = []

    # Clause 1: Keywords
    if config.inclusion_keywords:
        query_clauses.append(f"({' OR '.join(config.inclusion_keywords)})")
    
    # Clause 2: Authors
    if config.authors:
        # Scholar is better with author names as simple keywords
        query_clauses.append(f"({' OR '.join(config.authors)})")
    
    # Clause 3: Venues
    if config.venues:
        query_clauses.append(f"({' OR '.join(config.venues)})")

    # Clause 4: Macro Areas
    if config.macro_areas:
        query_clauses.append(f"({' OR '.join(config.macro_areas)})")

    if not query_clauses:
        log.warning("Google Scholar search requires keywords, authors, venues, or macro areas.")
        return []

    # Final Query: (Clause 1) (Clause 2) ... (space implies AND)
    query = " ".join(query_clauses)
    log.info(f"Constructed Google Scholar query: {query}")
    year_low, year_high = None, None
    if config.years:
        if isinstance(config.years, int): year_low = year_high = config.years
        elif isinstance(config.years, tuple): year_low, year_high = config.years

    log.info(f"Searching Google Scholar with query: '{query}'")

    search_results = scholarly.search_pubs(query, year_low=year_low, year_high=year_high)
    results_iterator = islice(search_results, config.max_results)

    results = []
    for pub in tqdm(results_iterator, desc="Fetching Scholar results"):
        bib = pub.get('bib', {})
        title = bib.get('title', 'No Title')
        abstract = bib.get('abstract', '')
        full_text_lower = (title + " " + abstract).lower()
        if config.exclusion_keywords and any(ex_k.lower() in full_text_lower for ex_k in config.exclusion_keywords): 
            continue

        paper_authors = bib.get('author', [])
        if isinstance(paper_authors, str): paper_authors = [name.strip() for name in paper_authors.split(' and ')]
        
        results.append(Paper(
            title=title, authors=paper_authors,
            year=int(bib['pub_year']) if bib.get('pub_year') and str(bib['pub_year']).isdigit() else None,
            venue=bib.get('venue'), url=pub.get('pub_url') or pub.get('eprint_url'),
            summary=abstract, source="Google Scholar"
        ))

    return results