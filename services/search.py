from collections.abc import Iterable
from typing import Protocol

from models.library import Library


class LibraryFilter(Protocol):
    def matches(self, library: Library) -> bool:
        pass


class KeywordFilter:
    def __init__(self, keyword: str):
        self.keyword = str(keyword or "").strip()

    def matches(self, library: Library) -> bool:
        return not self.keyword or library.matches_keyword(self.keyword)


class DistrictFilter:
    def __init__(self, district):
        self.district = district

    def matches(self, library: Library) -> bool:
        return (
            not self.district
            or self.district == "All districts"
            or library.district == self.district
        )


def create_library_filters(keyword: str, district: str) -> tuple[LibraryFilter, DistrictFilter]:
    return KeywordFilter(keyword), DistrictFilter(district)


def filter_libraries(
    libraries: Iterable[Library], filters: Iterable[LibraryFilter]
) -> list[Library]:
    filters = tuple(filters)
    return [
        library
        for library in libraries
        if all(library_filter.matches(library) for library_filter in filters)
    ]

def search_libraries(libraries, keyword):
    return filter_libraries(libraries, [KeywordFilter(keyword)])


def filter_by_district(libraries, district):
    return filter_libraries(libraries, [DistrictFilter(district)])


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
