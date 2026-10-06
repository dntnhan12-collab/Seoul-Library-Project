import pandas as pd
def search_library(df, library_name):
    query = " ".join(str(library_name or "").split()).casefold()
    if not query:
        return df.iloc[0:0].copy()
    names = (
        df["Library_Name"]
        .fillna("")
        .astype(str)
        .str.split()
        .str.join(" ")
        .str.casefold()
    )
    return df[names.str.startswith(query)].copy()