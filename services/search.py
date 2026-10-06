def search_libraries(libraries, keyword):
    return [
        library for library in libraries
        if library.matches_keyword(keyword)
    ]


def filter_by_district(libraries, district):
    if not district or district == "All districts":
        return libraries

    return [
        library for library in libraries
        if library.district == district
    ]


def find_exact_libraries(df, library_name):
    query = " ".join(str(library_name or "").split()).casefold()
    if not query:
        return df.copy()
    names = (
        df["Library_Name"]
        .fillna("")
        .astype(str)
        .str.split()
        .str.join(" ")
        .str.casefold()
    )
    return df[names.str.contains(query, regex=False, na=False)].copy()
