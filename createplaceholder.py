import pandas as pd

df = pd.DataFrame({
    "Sta_ID": ["A", "B"],
    "Year": [2000, 2000],
    "Lat_Dec": [32.7, 33.1],
    "Lon_Dec": [-117.2, -118.0],
    "health_score": [80, 45]
})

df.to_csv("placeholder.csv", index=False)