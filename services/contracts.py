"""Small contracts consumed by data cleaning and library filtering."""

from abc import ABC, abstractmethod

import pandas as pd

from models.library import Library


class LibraryDataSource(ABC):
    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Return the library table with the project's CSV columns."""


class LibraryFilter(ABC):
    @abstractmethod
    def matches(self, library: Library) -> bool:
        """Return True when the library passes this filter."""
