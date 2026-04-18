-- Athena Table Creation Script
-- Point this to your S3 bucket location

CREATE EXTERNAL TABLE IF NOT EXISTS ocean_health_db.ocean_health_observations (
  year INT,
  lat DOUBLE,
  lon DOUBLE,
  temperature DOUBLE,
  oxygen DOUBLE,
  ph DOUBLE,
  salinity DOUBLE,
  health_score DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://your-ocean-health-bucket/processed_data/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Sample Query for Validation
SELECT year, AVG(temperature) as avg_temp, AVG(health_score) as avg_health
FROM ocean_health_db.ocean_health_observations
GROUP BY year
ORDER BY year DESC;
