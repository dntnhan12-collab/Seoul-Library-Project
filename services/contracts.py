"""Small contracts consumed by data cleaning and library filtering."""

from typing import Protocol

import pandas as pd

from models.library import Library


class LibraryDataSource(Protocol):
    def load(self) -> pd.DataFrame:
        """Return an independent snapshot with the project's library CSV columns.

        Preserve raw values for the shared cleaning step. Repeated calls must
        work; changing a returned frame must not change the source. An empty
        result must still include the columns. Report read failures by raising
        an exception, never by returning None or silently returning empty data.
        """
        ...


class LibraryFilter(Protocol):
    def matches(self, library: Library) -> bool:
        """Accept any Library and return a bool without modifying it.

        Repeated calls with the same library and filter settings give the same
        result. Implementations may use different selection criteria.
        """
        ...
