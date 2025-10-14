from datetime import datetime
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from litrev.models import SearchConfig, ZoteroPaper
from litrev.engine import run_search_pipeline, SEARCH_SOURCES
from litrev.utils import group_papers_by_title, auto_resolve_conflict
from litrev.zotero_enrichment import enrich_papers_with_zotero

# Load environment variables from .env file at the very start
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="LitRev Search",
    page_icon="📚",
    layout="wide",
)

# --- App Header ---
st.title("📚 LitRev")
st.markdown("Your single entry point for searching across major academic archives.")

# --- Constants for UI ---
AVAILABLE_MACRO_AREAS = sorted([
    "Computer Science", "Physics", "Mathematics", "Quantitative Biology",
    "Quantitative Finance", "Statistics", "Electrical Engineering", "Economics",
    "Engineering", "Medicine", "Neuroscience", "Social Sciences",
])
AVAILABLE_SOURCES = [source['name'] for source in SEARCH_SOURCES]

if 'keyword_groups' not in st.session_state:
    st.session_state.keyword_groups = []

# --- Search Form in the Sidebar ---
with st.sidebar:
    st.header("Search Parameters")
    
    # --- 1. Source Selection ---
    st.subheader("1. Select Sources")
    cols = st.columns(2)
    source_selections = {}
    for i, source in enumerate(AVAILABLE_SOURCES):
        with cols[i % 2]:
            source_selections[source] = st.checkbox(source, value=True, key=f"source_{source}")
    st.markdown("---")
    active_sources = [source for source, is_selected in source_selections.items() if is_selected]

    # --- 2. Query Definition ---
    st.subheader("2. Define Query")
    st.markdown("**Inclusion Keywords**")
    st.info("Each group is an AND-set. Multiple groups are OR'd together.")
    with st.form("new_keyword_group_form"):
        new_group_str = st.text_input("Add a new keyword group (comma-separated AND terms)", placeholder="e.g., cultural bias, large language models")
        if st.form_submit_button("Add Group"):
            if new_group_str:
                new_group = [k.strip() for k in new_group_str.split(',') if k.strip()]
                st.session_state.keyword_groups.append(new_group)
                st.rerun() # Rerun to update the UI
    
    # Display current groups with delete buttons
    for i, group in enumerate(st.session_state.keyword_groups):
        cols = st.columns([0.85, 0.15])
        with cols[0]:
            st.info(f"{', '.join(group)}")
        with cols[1]:
            if st.button("❌", key=f"delete_group_{i}", help=f"Remove this group"):
                st.session_state.keyword_groups.pop(i)
                st.rerun() # Rerun to update the UI
    exclude_str = st.text_input("Exclusion Keywords (comma-separated)", placeholder="e.g., vision, medical")
    authors_str = st.text_input("Authors (comma-separated)", placeholder="e.g., Yann LeCun, Geoffrey Hinton")
    venue_str = st.text_input("Venues (comma-separated)", placeholder="e.g., NeurIPS, ICLR, ACL")
    
    with st.expander("Select Macro Areas (optional)"):
        cols = st.columns(2)
        area_selections = {}
        for i, area in enumerate(AVAILABLE_MACRO_AREAS):
            with cols[i % 2]:
                area_selections[area] = st.checkbox(area, value=False, key=f"area_{area}")
    custom_areas_str = st.text_input("Custom Macro Areas (comma-separated)", placeholder="e.g., Cognitive Science")
    
    # --- 3. Filters & Preferences ---
    st.markdown("---")
    st.subheader("3. Filters & Preferences")
    year_mode = st.radio("Filter by Year", ["All Years", "Single Year", "Year Range"], key="year_mode")
    years_config = None
    if year_mode == "Single Year":
        years_config = st.number_input("Year", min_value=1950, max_value=datetime.now().year, value=datetime.now().year)
    elif year_mode == "Year Range":
        years_config = st.slider("Select a year range", 1950, datetime.now().year, (2020, datetime.now().year))
    
    max_results = st.slider("Max Results to Fetch", min_value=5, max_value=1000, value=20)
    
    st.markdown("---")
    st.subheader("4. Conflict Resolution")
    st.info("Set a priority for each selected source. Lower numbers are preferred.")
    source_priorities = {}
    if active_sources:
        for source in active_sources:
            source_priorities[source] = st.number_input(f"Priority for {source}", min_value=1, value=1, key=f"pref_{source}")
    else:
        st.warning("Please select at least one source to search.")

    search_button = st.button("Search", type="primary", use_container_width=True)

# --- Main Content Area ---

# Step 1: Execute search when the button is pressed
if search_button:
    # Collect data from all widgets
    selected_sources = [source for source, is_selected in source_selections.items() if is_selected]
    selected_macro_areas = [area for area, is_selected in area_selections.items() if is_selected]
    custom_areas = [m.strip() for m in custom_areas_str.split(',') if m.strip()]
    final_macro_areas = sorted(list(set(selected_macro_areas + custom_areas)))
    
    preferred_sources = [source for source, priority in sorted(source_priorities.items(), key=lambda item: item[1])]

    inclusion_keywords = []
    if st.session_state.keyword_groups:
        inclusion_keywords = [group for group in st.session_state.keyword_groups if group]
    config = SearchConfig(
        inclusion_keywords=inclusion_keywords,
        exclusion_keywords=[k.strip() for k in exclude_str.split(',') if k.strip()],
        authors=[a.strip() for a in authors_str.split(',') if a.strip()],
        venues=[v.strip() for v in venue_str.split(',') if v.strip()],
        macro_areas=final_macro_areas,
        sources_to_search=selected_sources,
        years=years_config,
        max_results=max_results
    )

    progress_bar = st.progress(0, text="Starting search...")
    def update_progress(fraction, text):
        progress_bar.progress(fraction, text=text)

    with st.spinner("Querying archives..."):
        all_papers, errors, queries = run_search_pipeline(config, progress_callback=update_progress)
        grouped_papers = group_papers_by_title(all_papers)
        
        resolved_papers = [group[0] for group in grouped_papers.values() if len(group) == 1]
        unresolved_conflicts = {}
        conflicts = {title: group for title, group in grouped_papers.items() if len(group) > 1}
        
        for title, group in conflicts.items():
            auto_choice = auto_resolve_conflict(group, preferred_sources)
            if auto_choice:
                resolved_papers.append(auto_choice)
            else:
                unresolved_conflicts[title] = group
        
        st.session_state.conflicts = unresolved_conflicts
        st.session_state.resolved_by_auto = resolved_papers
        st.session_state.errors = errors
        st.session_state.queries = queries
        st.session_state.conflicts_resolved = not unresolved_conflicts
        st.session_state.is_enriched = False # Reset enrichment status on new search
        if not unresolved_conflicts:
            st.session_state.final_results = resolved_papers
    
    progress_bar.empty()
    
# Step 2: Display errors and queries
if 'errors' in st.session_state and st.session_state.errors:
    st.header("⚠️ Search Errors")
    for error_msg in st.session_state.errors:
        st.error(error_msg)
    st.markdown("---")
    
if 'queries' in st.session_state and st.session_state.queries:
    with st.expander("🔍 View Final API Queries"):
        st.json(st.session_state.queries)
    st.markdown("---")
    
# Step 3: Show conflict resolution form if needed
if st.session_state.get('conflicts') and not st.session_state.get('conflicts_resolved'):
    st.header(f"{len(st.session_state.conflicts)} unresolved duplicates require manual selection")
    
    with st.form("conflict_form"):
        for i, (title, group) in enumerate(st.session_state.conflicts.items()):
            options = [f"Keep from **{p.source}** (URL: {p.url or 'N/A'})" for p in group]
            st.radio(f"**{i+1}. {group[0].title}**", options, key=f"conflict_choice_{i}")
        
        if st.form_submit_button("Resolve Duplicates", type="primary"):
            final_papers = st.session_state.resolved_by_auto.copy()
            for i, group in enumerate(st.session_state.conflicts.values()):
                selected_option_string = st.session_state[f"conflict_choice_{i}"]
                options_list = [f"Keep from **{p.source}** (URL: {p.url or 'N/A'})" for p in group]
                chosen_index = options_list.index(selected_option_string)
                final_papers.append(group[chosen_index])
            
            st.session_state.final_results = final_papers
            st.session_state.conflicts_resolved = True
            st.rerun()

# Step 4: Display final results
if st.session_state.get('conflicts_resolved'):
    results = st.session_state.get('final_results', [])
    is_enriched = st.session_state.get('is_enriched', False)
    
    st.header(f"Final Results ({len(results)} unique papers)")

    if results and not is_enriched:
        st.markdown("---")
        if st.button("✨ Enrich Results with Zotero", help="Uses the Zotero translation server to fetch standardized metadata for each paper."):
            
            # 1. Create a progress bar placeholder
            st_progress_bar = st.progress(0, text="Starting enrichment...")
            
            # 2. Define the callback function that updates the bar
            def update_st_progress(fraction, text):
                st_progress_bar.progress(fraction, text=text)

            # Use a spinner for the overall process
            with st.spinner("Enriching papers with Zotero... This may take a while."):
                # 3. Pass the callback to the enrichment function
                enriched_results = enrich_papers_with_zotero(results, progress_callback=update_st_progress)
                
                # Update session state
                st.session_state.final_results = enriched_results
                st.session_state.is_enriched = True
            
            # 4. Remove the progress bar and rerun to display the final results
            st_progress_bar.empty()
            st.rerun()
    st.markdown("---")

    if not results:
        if not st.session_state.get('errors'):
             st.warning("No papers matched your search criteria.")
    else:
        results.sort(key=lambda p: (p.display_year or 0, p.display_title.lower()), reverse=True)
        
        # --- PREPARE DATA FOR DISPLAY AND DOWNLOAD ---
        
        # 1. Prepare data for the display table (as before)
        display_data = []
        for p in results:
            source = p.source
            if isinstance(p, ZoteroPaper) and p.title:
                source = f"{source} (Enriched)"
            display_data.append({
                'Source': source, 'Year': p.display_year, 'Title': p.display_title,
                'Authors': ', '.join(p.display_authors), 'Venue': p.display_venue,
                'URL': p.display_url, 'Summary': p.display_summary,
            })
        df_display = pd.DataFrame(display_data)

        # 2. Prepare a separate, clean DataFrame specifically for ASReview
        asreview_data = []
        for p in results:
            asreview_data.append({
                'title': p.display_title,
                'abstract': p.display_summary,
                'authors': '; '.join(p.display_authors), # Use semicolon as a robust separator
                'year': p.display_year,
                'doi': p.DOI if isinstance(p, ZoteroPaper) else None,
                'url': p.display_url,
                'included': '' # Add the crucial empty column for labeling
            })
        df_asreview = pd.DataFrame(asreview_data)

        # --- CREATE TABS FOR DIFFERENT VIEWS ---
        tab1, tab2 = st.tabs(["📄 Summary Table", "📑 Detailed View"])

        with tab1:
            st.markdown("A sortable and searchable table of the results.")
            st.dataframe(df_display, column_config={"URL": st.column_config.LinkColumn("Link")}, hide_index=True, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Download Results")
            
            # --- ADD TWO SEPARATE DOWNLOAD BUTTONS ---
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Download Display Table (CSV)",
                    data=df_display.to_csv(index=False).encode('utf-8'),
                    file_name=f"litrev_results_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv',
                    use_container_width=True,
                    help="Downloads the data exactly as shown in the table above."
                )
            with col2:
                st.download_button(
                    label="⭐ Download for ASReview (CSV)",
                    data=df_asreview.to_csv(index=False).encode('utf-8'),
                    file_name=f"asreview_import_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv',
                    use_container_width=True,
                    help="Downloads the data in a format optimized for import into ASReview, including the required 'included' column."
                )

        with tab2:
            st.markdown("An expandable view for each paper's abstract and details.")
            for i, paper in enumerate(results):
                with st.expander(f"[{paper.source}] **{paper.display_title}**"):
                    st.markdown(f"**Authors**: {', '.join(paper.display_authors)}")
                    st.markdown(f"**Year**: {paper.display_year or 'N/A'} | **Publication**: {paper.display_venue or 'N/A'}")
                    if isinstance(paper, ZoteroPaper) and paper.DOI:
                        st.markdown(f"**DOI**: {paper.DOI}")
                    if paper.display_summary:
                        st.markdown(f"**Abstract**: {paper.display_summary}")
                    if paper.display_url:
                        st.link_button("View Source", paper.display_url)