# lit_rev/models.py
from typing import List, Optional, Tuple, Union, Dict
from pydantic import BaseModel, Field

class SearchConfig(BaseModel):
    """Unified configuration for all paper searches."""
    inclusion_keywords: List[str] = Field(default_factory=list)
    exclusion_keywords: List[str] = Field(default_factory=list)
    authors: List[str] = Field(default_factory=list)
    years: Optional[Union[int, Tuple[int, int]]] = None
    venues: List[str] = Field(default_factory=list)
    macro_areas: List[str] = Field(default_factory=list)
    sources_to_search: List[str] = Field(default_factory=list)
    max_results: int = 20

class Paper(BaseModel):
    """The base representation of a paper from any source."""
    title: str
    authors: List[str]
    year: Optional[int] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    source: str

    # --- Add Properties for a Consistent UI Interface ---
    @property
    def display_title(self) -> str:
        return self.title

    @property
    def display_authors(self) -> List[str]:
        return self.authors

    @property
    def display_year(self) -> Optional[int]:
        return self.year
        
    @property
    def display_venue(self) -> Optional[str]:
        return self.venue

    @property
    def display_summary(self) -> Optional[str]:
        return self.summary

    @property
    def display_url(self) -> Optional[str]:
        return self.url
    
class ZoteroCreator(BaseModel):
    """Represents a Zotero creator (e.g., author, editor)."""
    creatorType: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None

class ZoteroPaper(BaseModel):
    """
    A detailed, standardized paper model based on Zotero's output.
    """
    source_paper: Paper
    itemType: Optional[str] = None
    title: Optional[str] = None
    creators: List[ZoteroCreator] = Field(default_factory=list)
    abstractNote: Optional[str] = None
    publicationTitle: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    date: Optional[str] = None
    DOI: Optional[str] = None
    url: Optional[str] = None
    libraryCatalog: Optional[str] = None
    accessDate: Optional[str] = None
    tags: List[Dict] = Field(default_factory=list)

    # --- NEW: Add Properties for a Consistent UI Interface ---
    
    @property
    def source(self) -> str:
        """Provides a consistent way to get the original source name."""
        return self.source_paper.source

    @property
    def display_title(self) -> str:
        return self.title or self.source_paper.title

    @property
    def display_authors(self) -> List[str]:
        if self.creators:
            return [f"{c.firstName or ''} {c.lastName or ''}".strip() for c in self.creators]
        return self.source_paper.authors

    @property
    def display_year(self) -> Optional[int]:
        if self.date and self.date.split('-')[0].isdigit():
            return int(self.date.split('-')[0])
        return self.source_paper.year
        
    @property
    def display_venue(self) -> Optional[str]:
        return self.publicationTitle or self.source_paper.venue

    @property
    def display_summary(self) -> Optional[str]:
        return self.abstractNote or self.source_paper.summary

    @property
    def display_url(self) -> Optional[str]:
        return self.url or self.source_paper.url