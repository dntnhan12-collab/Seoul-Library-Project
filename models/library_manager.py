from models.library import Library

class LibraryManager:
    def __init__(self, libraries):
        self.libraries = libraries
    @classmethod
    def from_dataframe(cls, df):
        libraries = []
    
        for _, row in df.iterrows():
                library = Library.from_row(row)
                libraries.append(library)
    
        return cls(libraries)

    def get_all(self):
        return self.libraries

    def filter_by_district(self, district):
        return [
            library for library in self.libraries
            if library.district == district
        ]

    def search(self, keyword):
        return [
            library for library in self.libraries
            if library.matches_keyword(keyword)
        ]
    
