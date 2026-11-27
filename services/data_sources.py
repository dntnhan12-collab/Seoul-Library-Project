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
