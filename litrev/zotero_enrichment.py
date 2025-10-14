import logging
import re
from typing import List, Tuple, Optional, Callable
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from litrev.models import Paper, ZoteroPaper

TRANSLATION_SERVER_URL = "http://localhost:1969/web"

def _enrich_single_paper(paper: Paper) -> Tuple[bool, ZoteroPaper]:
    """
    Worker function to enrich a single paper.
    Returns a tuple: (success_status, ZoteroPaper_object).
    """
    # --- 1. Pre-filter invalid URLs before making a request ---
    if not paper.url or not paper.url.startswith(('http://', 'https://')):
        return False, ZoteroPaper(source_paper=paper) # Failure, wrap original
    
    # Skip direct PDF links, as the server will reject them.
    if paper.url.lower().endswith('.pdf'):
        return False, ZoteroPaper(source_paper=paper)

    # Pre-process ArXiv links for better success rate
    processed_url = re.sub(r'arxiv.org/pdf/([\d.]+)', r'arxiv.org/abs/\1', paper.url)

    try:
        headers = {'Content-Type': 'text/plain'}
        response = requests.post(TRANSLATION_SERVER_URL, data=processed_url, headers=headers, timeout=20)

        # 4xx and 5xx errors will be caught by raise_for_status()
        response.raise_for_status()
        
        zotero_data_list = response.json()
        if not zotero_data_list:
            return False, ZoteroPaper(source_paper=paper) # Failure, but not an error

        # Success!
        return True, ZoteroPaper(source_paper=paper, **zotero_data_list[0])

    except requests.exceptions.RequestException:
        # This catches all network errors, timeouts, and non-200 status codes
        return False, ZoteroPaper(source_paper=paper) # Failure, wrap original

def enrich_papers_with_zotero(
    papers: List[Paper], 
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> List[ZoteroPaper]:
    """
    Enriches a list of papers concurrently, reporting progress via an optional callback.
    """
    log = logging.getLogger(__name__)
    log.info(f"Starting Zotero enrichment for {len(papers)} papers...")
    
    enriched_results = []
    success_count = 0
    total_papers = len(papers)
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_paper = {executor.submit(_enrich_single_paper, paper): paper for paper in papers}
        
        # tqdm is still great for the console log where the server is running.
        progress_bar = tqdm(as_completed(future_to_paper), total=total_papers, desc="Enriching papers with Zotero")
        
        for i, future in enumerate(progress_bar):
            paper = future_to_paper[future]
            try:
                success, enriched_paper = future.result()
                if success:
                    success_count += 1
                enriched_results.append(enriched_paper)

                # --- THIS IS THE KEY CHANGE ---
                # If a callback was provided, call it with the current progress.
                if progress_callback:
                    progress_fraction = (i + 1) / total_papers
                    progress_text = f"Enriching paper {i + 1} of {total_papers}..."
                    progress_callback(progress_fraction, progress_text)
                # ---------------------------

            except Exception as e:
                log.error(f"An unexpected error occurred for paper '{paper.title}': {e}")
                enriched_results.append(ZoteroPaper(source_paper=paper))

    log.info(f"Zotero enrichment complete. Successfully enriched {success_count}/{total_papers} papers.")
    return enriched_results