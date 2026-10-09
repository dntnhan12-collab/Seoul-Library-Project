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
    
