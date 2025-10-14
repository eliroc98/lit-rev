import logging
from typing import List, Optional, Dict
from acl_anthology import Anthology
from tqdm import tqdm
from litrev.models import SearchConfig, Paper
from litrev.utils import robust_search

@robust_search()
def search_acl(config: SearchConfig, query_log: Optional[Dict[str, str]] = None) -> List[Paper]:
    """
    Searches the ACL Anthology using a client-side "AND of ORs" filter,
    mirroring the logic of the API-based search modules.
    """
    log = logging.getLogger(__name__)
    log.info("Initializing ACL Anthology (this may take a moment)...")
    if config.macro_areas:
        log.warning("ACL Anthology is specific to NLP/CL; the 'macro_area' filter will be ignored for this source.")
    if query_log is not None:
        query_log["ACL Anthology"] = "Client-side filtering of all papers."
        
    anthology = Anthology.from_repo()
    all_papers = list(anthology.papers())
    
    results = []
    for paper in tqdm(all_papers, desc="Processing ACL Anthology"):
        # --- 1. Mandatory Filters (run these first for efficiency) ---
        paper_year_str = paper.year
        if not paper_year_str: continue
        paper_year = int(paper_year_str)
        if config.years:
            if isinstance(config.years, int) and paper_year != config.years: continue
            if isinstance(config.years, tuple) and not (config.years[0] <= paper_year <= config.years[1]): continue

        title = str(paper.title)
        abstract = str(paper.abstract) if hasattr(paper, 'abstract') and paper.abstract else ""
        full_text_lower = (title + " " + abstract).lower()

        if config.exclusion_keywords and any(ex_k.lower() in full_text_lower for ex_k in config.exclusion_keywords): 
            continue

        # --- 2. "AND of ORs" Filtering Logic ---
        # A paper must pass the check for each category provided by the user.

        # Keyword Check: Paper must match at least one of the AND-groups.
        if config.inclusion_keywords:
            keyword_match = False
            for group in config.inclusion_keywords:
                if all(term.lower() in full_text_lower for term in group):
                    keyword_match = True
                    break # Found a matching group, this check passes
            if not keyword_match:
                continue # If no keyword group matched, discard this paper

        # Author Check: Paper must match at least one of the specified authors.
        if config.authors:
            author_names_str = " ".join([str(author.name).lower() for author in paper.authors])
            if not any(a.lower() in author_names_str for a in config.authors):
                continue # If no author matched, discard this paper

        # Venue Check: Paper must match at least one of the specified venues.
        if config.venues:
            parent_title = str(getattr(paper.parent, 'title', ""))
            venue_identifiers = [paper.collection_id or "", parent_title]
            venue_identifiers.extend(paper.venue_ids or [])
            venue_search_space = " ".join(venue_identifiers).lower()
            if not any(v.lower() in venue_search_space for v in config.venues):
                continue # If no venue matched, discard this paper

        # --- 3. If all checks passed, add the paper ---
        if paper.bibtype == "proceedings":
            continue # Exclude front-matter and proceedings volumes

        results.append(Paper(
            title=title,
            authors=[str(author.name) for author in paper.authors],
            year=paper_year,
            venue=paper.collection_id.split('.')[-1].upper() if paper.collection_id else None,
            url=paper.web_url,
            summary=abstract,
            source="ACL Anthology"
        ))
        
        # Stop processing if we have already found enough results
        if len(results) >= config.max_results:
            break

    return results