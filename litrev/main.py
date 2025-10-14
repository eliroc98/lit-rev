import typer
import warnings
import logging
import pandas as pd
from pathlib import Path
from typing import List, Optional, Union, Tuple, Dict
from dotenv import load_dotenv
from litrev.models import SearchConfig, Paper, ZoteroPaper
from litrev.engine import run_search_pipeline, SEARCH_SOURCES
from litrev.utils import setup_logging, group_papers_by_title, auto_resolve_conflict
from litrev.zotero_enrichment import enrich_papers_with_zotero

# --- SETUP ---
load_dotenv()
setup_logging()
warnings.filterwarnings("ignore", message="^Unknown TeX-math command:")
logging.getLogger("acl_anthology.text.texmath").setLevel(logging.ERROR)

app = typer.Typer(
    name="lit-rev",
    help="A CLI for searching academic papers and exporting for literature reviews.",
    add_completion=False,
)

AVAILABLE_SOURCES = [source['name'] for source in SEARCH_SOURCES]

# --- CORE CLI WORKFLOW FUNCTIONS ---

def _resolve_conflicts_cli(papers: List[Paper], preference_order: List[str]) -> List[Paper]:
    """Handles conflict resolution automatically and then interactively in the terminal."""
    grouped_papers = group_papers_by_title(papers)
    
    # Separate non-conflicts from conflicts
    resolved_papers = [group[0] for group in grouped_papers.values() if len(group) == 1]
    conflicts = {title: group for title, group in grouped_papers.items() if len(group) > 1}
    unresolved_conflicts = {}

    # --- 1. Auto-Resolution Pass ---
    for title, group in conflicts.items():
        auto_choice = auto_resolve_conflict(group, preference_order)
        if auto_choice:
            resolved_papers.append(auto_choice)
        else:
            unresolved_conflicts[title] = group

    # --- 2. Manual Resolution Pass (only for what's left) ---
    if unresolved_conflicts:
        typer.echo("\n" + "-"*30)
        typer.echo(typer.style(" ACTION REQUIRED: Found unresolved duplicates.", fg=typer.colors.YELLOW))
        typer.echo("Please choose which version to keep for each.")
        typer.echo("-" * 30)

        for i, (title, group) in enumerate(unresolved_conflicts.items()):
            typer.echo(f"\nConflict {i+1}: {title}")
            for j, paper in enumerate(group):
                typer.echo(f"  [{j+1}] Source: {paper.source}, Year: {paper.year}, URL: {paper.url or 'N/A'}")
            
            choice = typer.prompt("  ➡️  Enter the number of the version to keep", type=int, default=1)
            chosen_index = (choice - 1) if 0 < choice <= len(group) else 0
            resolved_papers.append(group[chosen_index])
            
    return resolved_papers

def _post_search_menu(papers: List[Paper]):
    """Displays a menu for post-search actions like enrichment and downloading."""
    if not papers:
        return

    while True:
        typer.echo("\n--- Post-Search Actions ---")
        typer.echo("[1] ✨ Enrich results with Zotero")
        typer.echo("[2] 💾 Download as Display CSV")
        typer.echo("[3] ⭐ Download for ASReview")
        typer.echo("[4] 👋 Exit")
        
        choice = typer.prompt("➡️  What would you like to do next?", type=int, default=4)
        
        if choice == 1:
            typer.echo("Enriching papers... This may take a while.")
            # Update the list in-place with the enriched results
            papers = enrich_papers_with_zotero(papers)
            typer.echo(typer.style("✅ Enrichment complete!", fg=typer.colors.GREEN))
            _print_cli_results(papers, [], {}) # Re-print the (now enriched) results
        
        elif choice == 2 or choice == 3:
            filename = ""
            if choice == 2:
                # Prepare DataFrame for display
                display_data = [{
                    'Source': p.source, 'Year': p.display_year, 'Title': p.display_title,
                    'Authors': ', '.join(p.display_authors), 'Venue': p.display_venue,
                    'URL': p.display_url, 'Summary': p.display_summary,
                } for p in papers]
                df = pd.DataFrame(display_data)
                filename = typer.prompt("Enter filename for Display CSV", default="litrev_results.csv")
            
            else: # choice == 3
                # Prepare DataFrame for ASReview
                asreview_data = [{
                    'title': p.display_title, 'abstract': p.display_summary,
                    'authors': '; '.join(p.display_authors), 'year': p.display_year,
                    'doi': p.DOI if isinstance(p, ZoteroPaper) else None, 'url': p.display_url,
                    'included': ''
                } for p in papers]
                df = pd.DataFrame(asreview_data)
                filename = typer.prompt("Enter filename for ASReview CSV", default="asreview_import.csv")

            try:
                df.to_csv(filename, index=False)
                typer.echo(typer.style(f"✅ Successfully saved results to '{Path(filename).resolve()}'", fg=typer.colors.GREEN))
            except Exception as e:
                typer.echo(typer.style(f"❌ Error saving file: {e}", fg=typer.colors.RED))

        elif choice == 4:
            typer.echo("Exiting.")
            raise typer.Exit()
        
        else:
            typer.echo("Invalid choice. Please try again.")

def _print_cli_results(papers: List[Paper], errors: List[str], queries: Dict[str, str]):
    """Formats and prints the list of papers, errors, and queries to the console."""
    if queries:
        typer.echo("\n" + "-"*30)
        typer.echo("🔍 Final API Queries Sent:")
        for source, query in queries.items():
            typer.echo(f"  - {source}: {query}")
        typer.echo("-" * 30)
        
    if errors:
        typer.echo("\n" + "-"*30)
        typer.echo("⚠️ The following errors occurred during the search:")
        for error in errors:
            typer.echo(f"  - {error}")
        typer.echo("-" * 30)

    if not papers:
        typer.echo("\n❌ No papers matched all the specified criteria.")
        return
    
    typer.echo(f"\n✅ Found {len(papers)} unique matching papers:")
    typer.echo("-" * 30)
    for i, paper in enumerate(papers, 1):
        typer.echo(f"{i}. {paper.display_title} [{paper.source}]")
        typer.echo(f"   👤 Authors: {', '.join(paper.display_authors)}")
        typer.echo(f"   🗓️ Year: {paper.display_year or 'N/A'} | 🏛️ Venue: {paper.display_venue or 'N/A'}")
        if paper.display_url:
            typer.echo(f"   🔗 URL: {paper.display_url}")
        typer.echo("")

def run_cli_workflow(config: SearchConfig, preference_order: List[str]):
    """The main function that orchestrates the entire CLI workflow."""
    all_papers, errors, queries = run_search_pipeline(config)
    unique_papers = _resolve_conflicts_cli(all_papers, preference_order)
    _print_cli_results(unique_papers, errors, queries)
    _post_search_menu(unique_papers)

# --- CLI COMMANDS ---
@app.command()
def search(
    keyword_group: List[str] = typer.Option(None, "--keyword-group", "-kg", help="An AND-group of keywords (comma-separated). Repeat for OR logic."),
    exclude: List[str] = typer.Option(None, "--exclude", "-e", help="Keywords to exclude."),
    authors: List[str] = typer.Option(None, "--author", "-a", help="Author names."),
    venue: List[str] = typer.Option(None, "--venue", "-v", help="Venues (e.g., 'ICLR')."),
    macro_area: List[str] = typer.Option(None, "--macro-area", "-m", help="Broad subject areas."),
    source: List[str] = typer.Option(None, "--source", "-s", help=f"Specify sources to search."),
    year: Optional[int] = typer.Option(None, "-y", help="A single year."),
    start_year: Optional[int] = typer.Option(None, help="Start year for a range."),
    end_year: Optional[int] = typer.Option(None, help="End year for a range."),
    preferred_source: List[str] = typer.Option(None, "--preferred-source", "--pref", help="Source preference order for auto-resolving duplicates."),
    max_results: int = typer.Option(250, "-n", help="Max results per source."),
):
    """Search for papers using command-line arguments."""
    inclusion_keywords = []
    if keyword_group:
        for group_str in keyword_group:
            inclusion_keywords.append([k.strip() for k in group_str.split(',') if k.strip()])
    years_config = year if year else (start_year, end_year) if start_year and end_year else None
    config = SearchConfig(
        inclusion_keywords=inclusion_keywords or [], exclusion_keywords=exclude or [],
        authors=[a.strip().title() for a in (authors or [])], venues=venue or [],
        macro_areas=macro_area or [], sources_to_search=source or [],
        years=years_config, max_results=max_results
    )
    run_cli_workflow(config, preference_order=preferred_source or [])

@app.command()
def interactive():
    """Start an interactive session to guide you through a search."""
    print("--- 📚 Welcome to the Interactive Literature Search Wizard! ---")
    print("Please answer the following questions. Press Enter to skip.")
    
    typer.echo("\n--- Inclusion Keywords ---")
    typer.echo("Enter groups of AND-keywords. Multiple groups will be OR'd together.")
    inclusion_keywords = []
    while True:
        group_str = typer.prompt(f"➡️ Add keyword group {len(inclusion_keywords) + 1} (comma-separated), or press Enter to finish", default="")
        if not group_str:
            break
        inclusion_keywords.append([k.strip() for k in group_str.split(',') if k.strip()])
    exclude_str = typer.prompt("➡️ Keywords to exclude (comma-separated)", default="")
    authors_str = typer.prompt("➡️ Authors (name and surname, comma-separated)", default="")
    venue_str = typer.prompt("➡️ Venues (comma-separated)", default="")
    macro_area_str = typer.prompt("➡️ Macro Areas (e.g., Computer Science, Physics)", default="")
    typer.echo(f"\n➡️ Available sources: {', '.join(AVAILABLE_SOURCES)}")
    sources_str = typer.prompt("Which sources to search? (comma-separated, press Enter for all)", default="")
    selected_sources = [s.strip() for s in sources_str.split(',') if s.strip()]
    typer.echo("\n➡️ For duplicates, set a source preference order (e.g., 'ArXiv, DBLP')")
    pref_str = typer.prompt("Enter an ordered, comma-separated list, or press Enter to resolve all manually", default="")
    preference_order = [p.strip() for p in pref_str.split(',') if p.strip()]
    
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

    max_results: int = typer.prompt("\n➡️ Max results to return?", type=int, default=250)

    config = SearchConfig(
        inclusion_keywords=inclusion_keywords or [],
        exclusion_keywords=[k.strip() for k in exclude_str.split(',') if k.strip()],
        authors=[a.strip().title() for a in authors_str.split(',') if a.strip()],
        venues=[v.strip() for v in venue_str.split(',') if v.strip()],
        macro_areas=[m.strip() for m in macro_area_str.split(',') if m.strip()], # <-- Add this line
        years=years_config,
        sources_to_search=selected_sources,
        max_results=max_results
    )

    print("\n--- Search Configuration ---")
    print(config.model_dump_json(indent=2, exclude_defaults=True))
    if typer.confirm("\nDo you want to start the search with these settings?"):
        run_cli_workflow(config, preference_order)
    else:
        typer.echo("Search cancelled.")
        raise typer.Exit()

if __name__ == "__main__":
    app()