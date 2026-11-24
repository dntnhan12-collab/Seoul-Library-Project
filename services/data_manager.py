import pandas as pd

from services.contracts import LibraryDataSource


def get_cleaned_library_data(source: LibraryDataSource) -> pd.DataFrame:
    df = source.load()
    
    # Update columns directly instead of creating '_cleaned' versions
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    columns_to_check = ['Library_Name', 'District_Name', 'Latitude', 'Longitude']
    
    df_cleaned = df.dropna(subset=columns_to_check)
    return df_cleaned
