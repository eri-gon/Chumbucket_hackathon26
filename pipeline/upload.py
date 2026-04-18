import boto3
import pandas as pd
from botocore.exceptions import ClientError
import os

BUCKET = "datahacks26-ocean-health"
REGION = "us-west-2"
PROCESSED_DIR = "data/processed"

FILES = [
    "scores.parquet",
    "annual_means.parquet",
    "baseline_stats.parquet",
]


def load_credentials(csv_path="datahacks-2026_accessKeys.csv"):
    df = pd.read_csv(csv_path)
    key_id = df.iloc[0, 0].strip()
    secret  = df.iloc[0, 1].strip()
    return key_id, secret


def get_s3_client(key_id, secret):
    return boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
    )


def create_bucket(s3, bucket, region):
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"Bucket '{bucket}' already exists.")
    except ClientError:
        print(f"Creating bucket '{bucket}' in {region}...")
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
        print("Bucket created.")

    # Disable block public access so we can set public-read ACLs
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )


def upload_files(s3, bucket, processed_dir, files):
    base_url = f"https://{bucket}.s3.{REGION}.amazonaws.com"
    print()
    for fname in files:
        local_path = os.path.join(processed_dir, fname)
        s3_key = f"processed/{fname}"
        print(f"Uploading {fname}...")
        s3.upload_file(
            local_path,
            bucket,
            s3_key,
            ExtraArgs={"ACL": "public-read"},
        )
        print(f"  → {base_url}/{s3_key}")
    print("\nDone. Paste these URLs into app.py DATA_URLS.")


if __name__ == "__main__":
    key_id, secret = load_credentials()
    s3 = get_s3_client(key_id, secret)
    create_bucket(s3, BUCKET, REGION)
    upload_files(s3, BUCKET, PROCESSED_DIR, FILES)
