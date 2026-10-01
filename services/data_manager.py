import os
import pandas as pd
file_path = "data/seoul_library_english.csv"
df = pd.read_csv(file_path)

df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

columns_to_check = ['Library_Name', 'District_Name', 'Latitude', 'Longitude']
df_cleaned = df.dropna(subset=columns_to_check)

output_path = os.path.join('data', 'seoul_library_cleaned.csv')
df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
