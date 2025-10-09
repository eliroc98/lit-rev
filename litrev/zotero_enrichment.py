import logging
import re
from typing import List
import requests
from tqdm import tqdm
from litrev.models import Paper, ZoteroPaper

TRANSLATION_SERVER_URL = "http://localhost:1969/web"

def enrich_papers_with_zotero(papers: List[Paper]) -> List[ZoteroPaper]:
    """
    Enriches papers using the Zotero translation server by sending the URL
    as plain text in a POST request body.
    """
    log = logging.getLogger(__name__)
    log.info(f"Starting Zotero enrichment for {len(papers)} papers...")
    
    enriched_results = []
    
    for paper in tqdm(papers, desc="Enriching papers with Zotero"):
        if not paper.url or not paper.url.startswith(('http://', 'https://')):
            enriched_results.append(ZoteroPaper(source_paper=paper))
            continue

        processed_url = re.sub(r'arxiv.org/pdf/(\d+\.\d+)', r'arxiv.org/abs/\1', paper.url)

        try:
            # --- THIS IS THE FIX ---
            # Emulate the working cURL command.
            headers = {'Content-Type': 'text/plain'}
            # Use the `data` parameter to send the URL as the raw POST body.
            response = requests.post(TRANSLATION_SERVER_URL, data=processed_url, headers=headers, timeout=60)
            # ---------------------

            if response.status_code == 404:
                log.warning(f"Zotero could not find a translator for URL: {processed_url}")
                enriched_results.append(ZoteroPaper(source_paper=paper))
                continue

            response.raise_for_status()
            
            zotero_data_list = response.json()
            if not zotero_data_list:
                log.warning(f"Zotero returned no metadata for URL: {processed_url}")
                enriched_results.append(ZoteroPaper(source_paper=paper))
                continue

            enriched_paper = ZoteroPaper(source_paper=paper, **zotero_data_list[0])
            log.info(f"Successfully enriched paper: {enriched_paper.display_title}")
            enriched_results.append(enriched_paper)

        except requests.exceptions.RequestException as e:
            log.error(f"Could not enrich paper from URL {processed_url}: {e}")
            enriched_results.append(ZoteroPaper(source_paper=paper))

    log.info("Zotero enrichment complete.")
    return enriched_results