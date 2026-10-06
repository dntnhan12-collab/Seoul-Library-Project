import pandas as pd

def search_library(df: pd.DataFrame, library_name: str) -> pd.DataFrame:
    query = " ".join(str(library_name or "").split()).casefold()
    if not query:
        return df.iloc[0:0].copy()
    names = df["Library_Name"].fillna("").astype(str).map(
        lambda name: " ".join(name.split()).casefold()
    )
    return df.loc[names == query].copy()