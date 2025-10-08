import time
import functools
import logging

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
            return []
        return wrapper
    return decorator