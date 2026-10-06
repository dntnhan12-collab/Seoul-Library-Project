from pathlib import Path
import pandas as pd
BASE_DIR = Path(__file__).resolve().parent.parent
FILE_PATH = BASE_DIR / "data" / "seoul_library_english.csv"

def get_cleaned_library_data():
    df = pd.read_csv(FILE_PATH)
    
    # Update columns directly instead of creating '_cleaned' versions
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    columns_to_check = ['Library_Name', 'District_Name', 'Latitude', 'Longitude']
    
    df_cleaned = df.dropna(subset=columns_to_check)
    return df_cleaned
