import streamlit as st
import pandas as pd
from datetime import datetime
from litrev.models import SearchConfig
from litrev.engine import run_search_pipeline

# --- Page Configuration ---
st.set_page_config(
    page_title="LitRev Search",
    page_icon="📚",
    layout="wide",
)

# --- App Header ---
st.title("📚 LitRev: Unified Academic Search")
st.markdown("Your single entry point for searching across major academic archives.")

# --- Search Form in the Sidebar ---
with st.sidebar:
    st.header("Search Parameters")
    
    # Text-based inputs
    include_str = st.text_input("Inclusion Keywords (comma-separated)", placeholder="e.g., large language model, reasoning")
    exclude_str = st.text_input("Exclusion Keywords (comma-separated)", placeholder="e.g., vision, medical")
    authors_str = st.text_input("Authors (comma-separated)", placeholder="e.g., Yann LeCun, Geoffrey Hinton")
    venue_str = st.text_input("Venues (comma-separated)", placeholder="e.g., NeurIPS, ICLR, ACL")
    macro_area_str = st.text_input("Macro Areas", placeholder="e.g., Computer Science, Physics")

    # Year selection
    st.markdown("---")
    year_mode = st.radio("Filter by Year", ["All Years", "Single Year", "Year Range"], key="year_mode")
    years_config = None
    if year_mode == "Single Year":
        single_year = st.number_input("Year", min_value=1950, max_value=datetime.now().year, value=datetime.now().year)
        years_config = single_year
    elif year_mode == "Year Range":
        start_year, end_year = st.slider(
            "Select a year range",
            min_value=1950,
            max_value=datetime.now().year,
            value=(2020, datetime.now().year)
        )
        years_config = (start_year, end_year)

    # Max results
    st.markdown("---")
    max_results = st.slider("Max Results per Source", min_value=5, max_value=100, value=20)
    
    # Search button
    search_button = st.button("Search", type="primary", use_container_width=True)

# --- Main Content Area ---
if search_button:
    # Build the SearchConfig object from the UI inputs
    config = SearchConfig(
        inclusion_keywords=[k.strip() for k in include_str.split(',') if k.strip()],
        exclusion_keywords=[k.strip() for k in exclude_str.split(',') if k.strip()],
        authors=[a.strip() for a in authors_str.split(',') if a.strip()],
        venues=[v.strip() for v in venue_str.split(',') if v.strip()],
        macro_areas=[m.strip() for m in macro_area_str.split(',') if m.strip()],
        years=years_config,
        max_results=max_results
    )

    # Use a progress bar and spinner for better user feedback
    progress_bar = st.progress(0, text="Starting search...")
    
    def update_progress(fraction, text):
        progress_bar.progress(fraction, text=text)

    # Run the search and store results in session state to persist them
    with st.spinner("Querying archives..."):
        st.session_state.results = run_search_pipeline(config, progress_callback=update_progress)
    
    progress_bar.empty() # Clear the progress bar after completion

# --- Display Results ---
if 'results' in st.session_state:
    results = st.session_state.results
    
    st.header(f"Found {len(results)} unique papers")
    st.markdown("---")

    if not results:
        st.warning("No papers matched your search criteria.")
    else:
        # Optional: Display as a DataFrame
        # df = pd.DataFrame([p.model_dump() for p in results])
        # st.dataframe(df)
        
        # Display each paper in an expander for detail
        for i, paper in enumerate(results):
            with st.expander(f"**{i+1}. {paper.title}** [{paper.source}]"):
                st.markdown(f"**Authors**: {', '.join(paper.authors)}")
                st.markdown(f"**Year**: {paper.year or 'N/A'} | **Venue**: {paper.venue or 'N/A'}")
                if paper.summary:
                    st.markdown(f"**Abstract**: {paper.summary}")
                if paper.url:
                    st.link_button("View Source", paper.url)