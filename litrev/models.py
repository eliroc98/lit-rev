# lit_rev/models.py
from typing import List, Optional, Tuple, Union
from pydantic import BaseModel, Field

class SearchConfig(BaseModel):
    """Unified configuration for all paper searches."""
    inclusion_keywords: List[str] = Field(default_factory=list)
    exclusion_keywords: List[str] = Field(default_factory=list)
    authors: List[str] = Field(default_factory=list)
    years: Optional[Union[int, Tuple[int, int]]] = None
    venues: List[str] = Field(default_factory=list)
    macro_areas: List[str] = Field(default_factory=list)
    max_results: int = 20

class Paper(BaseModel):
    """A standardized representation of a paper."""
    title: str
    authors: List[str]
    year: Optional[int] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    source: str  # To track the origin (e.g., 'arXiv', 'DBLP')