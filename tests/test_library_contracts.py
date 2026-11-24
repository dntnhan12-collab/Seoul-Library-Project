import tempfile
import unittest
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from models.library_manager import LibraryManager
from services.analyzer import get_total_libraries
from services.data_manager import get_cleaned_library_data
from services.data_sources import CsvLibraryDataSource, DataFrameLibraryDataSource
from services.search import (
    DistrictFilter,
    KeywordFilter,
    create_library_filters,
    filter_libraries,
)


def sample_data():
    return pd.DataFrame({
        "Library_Serial_Number": [1, 2, 3],
        "Library_Name": ["Central Library", "River Library", "Invalid location"],
        "District_Name": ["Jongno", "Mapo", "Mapo"],
        "Address": ["1 Central Road", "2 River Road", "3 River Road"],
        "Phone_Number": ["111", "222", "333"],
        "Website_URL": ["https://example.org"] * 3,
        "Operating_Hours": ["09:00~18:00"] * 3,
        "Regular_Closed_Days": ["Monday"] * 3,
        "Library_Type_Name": ["Public"] * 3,
        "Latitude": ["37.57", "37.55", "invalid"],
        "Longitude": ["126.98", "126.91", "126.90"],
    })


class DataSourceContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.raw = sample_data()
        self.path = Path(self.directory.name) / "libraries.csv"
        self.raw.to_csv(self.path, index=False)
        self.sources = (
            CsvLibraryDataSource(self.path),
            DataFrameLibraryDataSource(self.raw),
        )

    def test_sources_are_substitutable_through_cleaning_models_and_search(self):
        for source in self.sources:
            with self.subTest(source=type(source).__name__):
                cleaned = get_cleaned_library_data(source)
                self.assertEqual(get_total_libraries(cleaned), 2)
                self.assertEqual(cleaned["Latitude"].tolist(), [37.57, 37.55])
                libraries = LibraryManager.from_dataframe(cleaned).get_all()
                result = filter_libraries(libraries, create_library_filters("River", "Mapo"))
                self.assertEqual([library.serial_number for library in result], [2])

    def test_load_returns_independent_repeatable_snapshots(self):
        for source in self.sources:
            with self.subTest(source=type(source).__name__):
                expected = source.load()
                changed = source.load()
                changed.loc[0, "Library_Name"] = "Changed"
                changed.drop(index=1, inplace=True)
                assert_frame_equal(source.load(), expected)
                get_cleaned_library_data(source)
                assert_frame_equal(source.load(), expected)

    def test_dataframe_source_isolated_from_callers_table(self):
        source = DataFrameLibraryDataSource(self.raw)
        expected = self.raw.copy(deep=True)
        self.raw.loc[0, "Library_Name"] = "Changed outside source"
        assert_frame_equal(source.load(), expected)

    def test_empty_sources_preserve_schema_and_support_pipeline(self):
        empty = self.raw.iloc[:0]
        empty.to_csv(self.path, index=False)
        for source in (CsvLibraryDataSource(self.path), DataFrameLibraryDataSource(empty)):
            with self.subTest(source=type(source).__name__):
                cleaned = get_cleaned_library_data(source)
                self.assertEqual(list(cleaned.columns), list(empty.columns))
                self.assertEqual(LibraryManager.from_dataframe(cleaned).get_all(), [])

    def test_missing_csv_raises_instead_of_looking_like_empty_data(self):
        with self.assertRaises(FileNotFoundError):
            get_cleaned_library_data(CsvLibraryDataSource(self.path.with_name("missing.csv")))

    def test_cleaner_accepts_source_with_only_load(self):
        raw = self.raw

        class LoadOnlySource:
            def load(self):
                return raw.copy(deep=True)

        # No inheritance, write/search methods, or filesystem access required.
        cleaned = get_cleaned_library_data(LoadOnlySource())
        self.assertEqual(cleaned["Library_Name"].tolist(), ["Central Library", "River Library"])
        self.assertEqual(raw.loc[0, "Latitude"], "37.57")


class FilterContractTests(unittest.TestCase):
    def setUp(self):
        cleaned = get_cleaned_library_data(DataFrameLibraryDataSource(sample_data()))
        self.libraries = LibraryManager.from_dataframe(cleaned).get_all()

    def test_builtin_filters_return_repeatable_bools_without_mutating_libraries(self):
        for library_filter in (KeywordFilter("River"), DistrictFilter("Mapo")):
            for library in self.libraries:
                with self.subTest(filter=type(library_filter).__name__, library=library.name):
                    before = vars(library).copy()
                    result = library_filter.matches(library)
                    self.assertIs(type(result), bool)
                    self.assertEqual(library_filter.matches(library), result)
                    self.assertEqual(vars(library), before)

    def test_builtin_filters_can_replace_each_other_in_same_consumer(self):
        for library_filter in (KeywordFilter(" rIvEr "), DistrictFilter("Mapo")):
            with self.subTest(filter=type(library_filter).__name__):
                self.assertEqual(filter_libraries(self.libraries, [library_filter]), [self.libraries[1]])

    def test_neutral_filters_accept_all_libraries(self):
        for library_filter in (KeywordFilter(""), DistrictFilter(""), DistrictFilter("All districts")):
            with self.subTest(filter=type(library_filter).__name__):
                self.assertEqual(filter_libraries(self.libraries, [library_filter]), self.libraries)

    def test_new_filter_needs_only_matches_and_composes_with_builtin_filters(self):
        class NorthernLibraryFilter:
            def matches(self, library):
                return library.latitude >= 37.56

        self.assertEqual(
            filter_libraries(self.libraries, [NorthernLibraryFilter(), KeywordFilter("Library")]),
            [self.libraries[0]],
        )
        self.assertEqual(
            filter_libraries(self.libraries, [NorthernLibraryFilter(), DistrictFilter("Mapo")]),
            [],
        )

    def test_iterable_filters_apply_to_every_library(self):
        filters = (item for item in (KeywordFilter("Library"), DistrictFilter("Mapo")))
        self.assertEqual(filter_libraries(iter(self.libraries), filters), [self.libraries[1]])
        self.assertEqual(filter_libraries([], create_library_filters("River", "Mapo")), [])


if __name__ == "__main__":
    unittest.main()
