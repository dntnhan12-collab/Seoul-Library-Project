def get_total_libraries(df):
    return len(df)

def get_total_districts(df):
    return df['District_Name'].nunique()

def get_libraries_per_district(df):
    return df.groupby("District_Name").size().sort_values(ascending=False)