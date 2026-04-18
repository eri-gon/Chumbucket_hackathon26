import pandas as pd
import numpy as np
import os

def generate_sample_data(num_records=1000):
    """Generates synthetic oceanographic data for testing the pipeline."""
    print(f"Generating {num_records} sample records...")
    
    years = np.random.randint(1950, 2022, num_records)
    # Southern California Bight coordinates approx
    lats = np.random.uniform(30.0, 35.0, num_records)
    lons = np.random.uniform(-125.0, -115.0, num_records)
    
    temp = np.random.uniform(8.0, 20.0, num_records)
    oxygen = np.random.uniform(1.0, 8.0, num_records)
    ph = np.random.uniform(7.8, 8.2, num_records)
    salinity = np.random.uniform(33.0, 35.0, num_records)
    
    # Simple Health Score calculation
    # Normalized sum of O2 and pH - higher is "healthier"
    health_score = (
        (oxygen - 1.0) / (8.0 - 1.0) * 0.5 + 
        (ph - 7.8) / (8.2 - 7.8) * 0.5
    ) * 100
    
    df = pd.DataFrame({
        'year': years,
        'lat': lats,
        'lon': lons,
        'temperature': temp,
        'oxygen': oxygen,
        'ph': ph,
        'salinity': salinity,
        'health_score': health_score
    })
    
    df.to_csv('processed_ocean_data.csv', index=False)
    print("Done! Saved to processed_ocean_data.csv")

def process_real_data(bottle_path, cast_path):
    """Aggregates and joins real CalCOFI data."""
    print("Loading data... this might take a moment.")
    
    # Load Cast data (Geolocation and Time)
    cast_cols = ['Cst_Cnt', 'Year', 'Lat_Dec', 'Lon_Dec']
    df_cast = pd.read_csv(cast_path, usecols=cast_cols)
    
    # Load Bottle data (Measurements)
    # We only take the columns we need to save memory
    bottle_cols = ['Cst_Cnt', 'T_degC', 'Salnty', 'O2ml_L', 'pH1']
    df_bottle = pd.read_csv(bottle_path, usecols=bottle_cols)
    
    print("Aggregating measurements per cast...")
    # Group by Cst_Cnt and take the mean
    df_bottle_agg = df_bottle.groupby('Cst_Cnt').mean().reset_index()
    
    print("Joining cast and bottle data...")
    df_final = pd.merge(df_cast, df_bottle_agg, on='Cst_Cnt', how='inner')
    
    # Rename columns for consistency
    df_final = df_final.rename(columns={
        'Year': 'year',
        'Lat_Dec': 'lat',
        'Lon_Dec': 'lon',
        'T_degC': 'temperature',
        'Salnty': 'salinity',
        'O2ml_L': 'oxygen',
        'pH1': 'ph'
    })
    
    # Drop rows with missing lat/lon
    df_final = df_final.dropna(subset=['lat', 'lon'])
    
    # Calculate Health Score
    # Handle NaNs before calculation
    df_final['oxygen_norm'] = (df_final['oxygen'] - df_final['oxygen'].min()) / (df_final['oxygen'].max() - df_final['oxygen'].min())
    df_final['ph_norm'] = (df_final['ph'] - df_final['ph'].min()) / (df_final['ph'].max() - df_final['ph'].min())
    df_final['health_score'] = (df_final['oxygen_norm'].fillna(0) * 0.5 + df_final['ph_norm'].fillna(0) * 0.5) * 100
    
    # Select final columns
    final_cols = ['year', 'lat', 'lon', 'temperature', 'oxygen', 'ph', 'salinity', 'health_score']
    df_final = df_final[final_cols]
    
    output_path = 'processed_ocean_data.csv'
    df_final.to_csv(output_path, index=False)
    print(f"Successfully processed {len(df_final)} records. Saved to {output_path}")

if __name__ == "__main__":
    BOTTLE_FILE = "194903-202105_Bottle.csv"
    CAST_FILE = "194903-202105_Cast.csv"
    
    # For hackathon speed/demo, we can toggle between real and sample data
    USE_REAL_DATA = False # Set to True to process the 175MB file
    
    if USE_REAL_DATA and os.path.exists(BOTTLE_FILE) and os.path.exists(CAST_FILE):
        try:
            process_real_data(BOTTLE_FILE, CAST_FILE)
        except Exception as e:
            print(f"Error processing real data: {e}")
            generate_sample_data()
    else:
        generate_sample_data()
