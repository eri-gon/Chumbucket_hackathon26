# 🌊 Ocean Health Query & Visualization Platform

An interactive system to monitor and visualize oceanographic health metrics using the CalCOFI dataset. Built for speed and scalability during the 2026 Ocean Hackathon.

## 🚀 Overview

This platform processes vast amounts of bottle and cast data to provide:
- **Interactive Map**: Geospatial visualization of sampling events.
- **Time-Series Analysis**: Trends in Temperature, Oxygen, and pH over decades.
- **Health Scoring**: A proprietary metric for assessing local ocean vitality.

## 🛠️ Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Database**: [AWS Athena](https://aws.amazon.com/athena/)
- **Data Storage**: AWS S3
- **Language**: Python (Pandas, Boto3, PyAthena)

## 📦 Setup & Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
2. Install dependencies:
   ```bash
   pip install streamlit boto3 pyathena pandas
   ```
3. Configure AWS:
   Ensure your AWS CLI is configured with the correct credentials. Use `.streamlit/secrets.toml` for app-specific secrets.
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## 🏗️ Architecture

1. `process_data.py`: Aggregates raw CSV data and uploads to S3.
2. `athena_setup.sql`: Configures the Athena table and partitions.
3. `app.py`: Main Streamlit application interfacing with Athena.
