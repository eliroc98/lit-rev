import logging
from typing import List
from acl_anthology import Anthology
from tqdm import tqdm
from litrev.models import SearchConfig, Paper
from litrev.utils import robust_search

@robust_search()
def search_acl(config: SearchConfig) -> List[Paper]:
    """Searches the ACL Anthology with a relevance ranking system."""
    log = logging.getLogger(__name__)
    log.info("Initializing ACL Anthology (this may take a moment)...")
    anthology = Anthology.from_repo()
    
    # Convert to list to get a total for the progress bar
    all_papers = list(anthology.papers())
    
    scored_papers = []
    for paper in tqdm(all_papers, desc="Processing ACL Anthology"):
        paper_year_str = paper.year
        if not paper_year_str: continue
        paper_year = int(paper_year_str)
        if config.years:
            if isinstance(config.years, int) and paper_year != config.years: continue
            if isinstance(config.years, tuple) and not (config.years[0] <= paper_year <= config.years[1]): continue
        title = str(paper.title)
        abstract = str(paper.abstract) if hasattr(paper, 'abstract') and paper.abstract else ""
        full_text_lower = (title + " " + abstract).lower()
        if config.exclusion_keywords and any(ex_k.lower() in full_text_lower for ex_k in config.exclusion_keywords): continue
        score = 0
        if config.inclusion_keywords: score += sum(1 for k in config.inclusion_keywords if k.lower() in full_text_lower)
        author_names_str = " ".join([str(author.name).lower() for author in paper.authors])
        if config.authors: score += sum(1 for a in config.authors if a.lower() in author_names_str)
        if config.venues:
            parent_title = str(getattr(paper.parent, 'title', ""))
            venue_identifiers = [paper.collection_id or "", parent_title]
            venue_identifiers.extend(paper.venue_ids or [])
            venue_search_space = " ".join(venue_identifiers).lower()
            score += sum(1 for v in config.venues if v.lower() in venue_search_space)
        if score > 0:
            paper_obj = Paper(
                title=title, authors=[str(author.name) for author in paper.authors], year=paper_year,
                venue=paper.collection_id, url=paper.web_url, summary=abstract, source="ACL Anthology"
            )
            scored_papers.append((score, paper_obj))

    scored_papers.sort(key=lambda x: x[0], reverse=True)
    final_results = [paper for score, paper in scored_papers]
    return final_results[:config.max_results]