from typing import List, Optional, Union, Tuple
import typer
import warnings
import logging
from litrev.models import SearchConfig, Paper
from litrev.engine import run_search_pipeline # <-- IMPORT THE NEW ENGINE
from litrev.utils import setup_logging # <-- For consistent logging

setup_logging()
warnings.filterwarnings("ignore", message="^Unknown TeX-math command:")
logging.getLogger("acl_anthology.text.texmath").setLevel(logging.ERROR)

app = typer.Typer(
    name="lit-rev",
    help="A CLI for searching academic papers across multiple archives.",
    add_completion=False
)

def _print_cli_results(papers: List[Paper]):
    """Formats and prints the list of papers to the console."""
    if not papers:
        print("\n❌ No papers matched all the specified criteria.")
        return
    print(f"\n✅ Found {len(papers)} unique matching papers:")
    print("-" * 30)
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title} [{paper.source}]")
        print(f"   👤 Authors: {', '.join(paper.authors)}")
        print(f"   🗓️ Year: {paper.year or 'N/A'} | 🏛️ Venue: {paper.venue or 'N/A'}")
        if paper.url:
            print(f"   🔗 URL: {paper.url}")
        print("")

def _print_results(papers: List[Paper]):
    """Formats and prints the list of papers."""
    if not papers:
        print("\n❌ No papers matched all the specified criteria.")
        return
    unique_papers = list({(p.url or p.title): p for p in papers}.values())
    print(f"\n✅ Found {len(unique_papers)} unique matching papers:")
    print("-" * 30)
    for i, paper in enumerate(unique_papers, 1):
        print(f"{i}. {paper.title} [{paper.source}]")
        print(f"   👤 Authors: {', '.join(paper.authors)}")
        print(f"   🗓️ Year: {paper.year or 'N/A'} | 🏛️ Venue: {paper.venue or 'N/A'}")
        if paper.url:
            print(f"   🔗 URL: {paper.url}")
        print("")

# --- ORIGINAL COMMAND (FOR POWER USERS) ---
@app.command()
def search(
    # (This command remains unchanged)
    include: List[str] = typer.Option(None, "--include", "-i", help="Keywords to include (repeat for multiple)."),
    exclude: List[str] = typer.Option(None, "--exclude", "-e", help="Keywords to exclude (repeat for multiple)."),
    authors: List[str] = typer.Option(None, "--author", "-a", help="Author names (repeat for multiple)."),
    venue: List[str] = typer.Option(None, "--venue", "-v", help="Venues (e.g., 'ICLR', 'NeurIPS')."),
    macro_area: List[str] = typer.Option(None, "--macro-area", "-m", help="Broad subject areas (e.g., 'Computer Science')."),
    year: Optional[int] = typer.Option(None, "-y", help="A single year."),
    start_year: Optional[int] = typer.Option(None, "--start-year", help="Start year for a range."),
    end_year: Optional[int] = typer.Option(None, "--end-year",help="End year for a range."),
    max_results: int = typer.Option(20, "-n", help="Max results per source."),
):
    """Search for papers using command-line arguments."""
    years_config = year if year else (start_year, end_year) if start_year and end_year else None
    config = SearchConfig(
        inclusion_keywords=include or [], exclusion_keywords=exclude or [],
        authors=[a.strip().title() for a in authors], venues=venue or [],
        macro_areas=macro_area or [], years=years_config, max_results=max_results
    )
    # --- CALL THE NEW ENGINE ---
    results = run_search_pipeline(config)
    _print_cli_results(results)

@app.command()
def interactive():
    """Start an interactive session to guide you through a search."""
    print("--- 📚 Welcome to the Interactive Literature Search Wizard! ---")
    print("Please answer the following questions. Press Enter to skip.")
    
    include_str = typer.prompt("\n➡️ Keywords to include (comma-separated)", default="")
    exclude_str = typer.prompt("➡️ Keywords to exclude (comma-separated)", default="")
    authors_str = typer.prompt("➡️ Authors (name and surname, comma-separated)", default="")
    venue_str = typer.prompt("➡️ Venues (comma-separated)", default="")
    macro_area_str = typer.prompt("➡️ Macro Areas (e.g., Computer Science, Physics)", default="")
    
    years_config: Optional[Union[int, Tuple[int, int]]] = None
    
    year_prompt = typer.prompt(
        "\n➡️ Search a single year (e.g., 2023), type 'r' for a range, or press Enter to skip",
        default="", show_default=False
    )

    if year_prompt.lower() == 'r':
        start_year: Optional[int] = typer.prompt("➡️ Start year for a range", type=int, default=None)
        if start_year is not None:
            end_year: int = typer.prompt(f"➡️ End year for the range (starting from {start_year})", type=int)
            years_config = (min(start_year, end_year), max(start_year, end_year))
    elif year_prompt.isdigit():
        years_config = int(year_prompt)

    max_results: int = typer.prompt("\n➡️ Max results to return?", type=int, default=20)

    config = SearchConfig(
        inclusion_keywords=[k.strip() for k in include_str.split(',') if k.strip()],
        exclusion_keywords=[k.strip() for k in exclude_str.split(',') if k.strip()],
        authors=[a.strip().title() for a in authors_str.split(',') if a.strip()],
        venues=[v.strip() for v in venue_str.split(',') if v.strip()],
        macro_areas=[m.strip() for m in macro_area_str.split(',') if m.strip()], # <-- Add this line
        years=years_config,
        max_results=max_results
    )

    print("\n--- Search Configuration ---")
    print(config.model_dump_json(indent=2, exclude_defaults=True))
    if typer.confirm("\nDo you want to start the search with these settings?"):
        results = run_search_pipeline(config)
        _print_cli_results(results)
    else:
        print("Search cancelled.")
        raise typer.Exit()

if __name__ == "__main__":
    app()