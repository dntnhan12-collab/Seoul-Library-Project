import pandas as pd


class LibraryStatistics:
    """Answers counting questions about one cleaned library table."""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def total_libraries(self) -> int:
        return len(self.df)

    def total_districts(self) -> int:
        return self.df["District_Name"].nunique()

    def libraries_per_district(self) -> pd.Series:
        return self.df.groupby("District_Name").size().sort_values(ascending=False)
