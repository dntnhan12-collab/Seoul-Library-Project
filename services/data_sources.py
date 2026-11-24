"""Data access adapters; cleaning belongs to data_manager."""

from pathlib import Path

import pandas as pd

from services.contracts import LibraryDataSource


FILE_PATH = Path(__file__).resolve().parent.parent / "data" / "seoul_library_english.csv"


class CsvLibraryDataSource(LibraryDataSource):
    def __init__(self, path: str | Path = FILE_PATH):
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        return pd.read_csv(self.path)


class DataFrameLibraryDataSource(LibraryDataSource):
    """Use an existing table, for example in a notebook or an offline test."""

    def __init__(self, data: pd.DataFrame):
        self._data = data.copy(deep=True)

    def load(self) -> pd.DataFrame:
        return self._data.copy(deep=True)
