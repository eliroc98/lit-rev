import time
import functools
import re
import logging
from collections import defaultdict
from typing import Optional, List, Dict
from litrev.models import Paper

def setup_logging():
    """
    Configures the root logger for persistent terminal output that works with tqdm.
    
    This uses the default StreamHandler which prints to the console and allows
    tqdm to manage its progress bars without overwriting the logs.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    
def group_papers_by_title(papers: List[Paper]) -> Dict[str, List[Paper]]:
    """
    Groups a list of papers by their title after robust normalization.

    Normalization steps:
    1. Converts to lowercase.
    2. Removes all punctuation.
    3. Normalizes all internal and external whitespace.
    """
    grouped_papers = defaultdict(list)
    for paper in papers:
        # 1. Start with the original title and convert to lowercase
        normalized_title = paper.title.lower()
        
        # 2. Remove all punctuation using a regular expression.
        # This will remove anything that is not a word character (\w) or whitespace (\s).
        normalized_title = re.sub(r'[^\w\s]', '', normalized_title)
        
        # 3. Normalize whitespace. This collapses multiple spaces into a single space
        # and removes any leading/trailing whitespace.
        normalized_title = " ".join(normalized_title.split())
        
        # Now, titles like "My Paper." and "my paper" will both become "my paper"
        grouped_papers[normalized_title].append(paper)
        
    return grouped_papers

def robust_search(retries: int = 3, delay: int = 3):
    """
    A decorator that makes a function resilient to transient errors by retrying.
    If all retries fail, it returns an empty list instead of crashing.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Use the module's logger name for better context in the logs
            log = logging.getLogger(func.__module__)
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    log.warning(f"An error occurred: {e}")
                    if attempt < retries - 1:
                        log.info(f"Retrying in {delay}s... (Attempt {attempt + 2}/{retries})")
                        time.sleep(delay)
                    else:
                        log.error(f"Failed after {retries} attempts.")
                        raise e
        return wrapper
    return decorator

def extract_year(text: str) -> Optional[int]:
    """
    Extracts the first likely year (a 4-digit number starting with 19 or 20)
    from a given string.

    Args:
        text: The string to search within.

    Returns:
        The extracted year as an integer, or None if no year is found.
    """
    if not isinstance(text, str):
        return None

    # This regex looks for a "word boundary", then "19" or "20", then two more digits,
    # followed by another "word boundary". This is the most reliable way to find a year.
    # \b -> word boundary (ensures we don't match part of a larger number like 'arXiv:2305.12345')
    # (19|20) -> matches either "19" or "20" for the century
    # \d{2} -> matches exactly two digits for the year
    match = re.search(r'\b(19|20)\d{2}\b', text)
    
    if match:
        # If a match is found, return it as an integer
        return int(match.group(0))
    
    # If no match is found, return None
    return None

def auto_resolve_conflict(group: List[Paper], preference_order: List[str]) -> Optional[Paper]:
    """
    Automatically selects a paper from a group of duplicates based on a preferred source order.

    Args:
        group: A list of Paper objects with the same title.
        preference_order: An ordered list of preferred source names (e.g., ["ArXiv", "DBLP"]).

    Returns:
        The highest-ranking paper from the group based on the preference order,
        or None if no paper in the group matches a preferred source.
    """
    if not preference_order:
        return None

    # Create a mapping of source name to paper for quick lookups
    papers_by_source = {paper.source: paper for paper in group}
    
    # Iterate through the user's preferred sources in order
    for source in preference_order:
        if source in papers_by_source:
            # The first match found is the highest-ranked preference
            return papers_by_source[source]
            
    # If no paper from a preferred source was found in this group
    return None