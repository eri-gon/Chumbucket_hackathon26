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
    "seasonal_scores.parquet",
]


def load_credentials(csv_path=".aws/credentials.csv"):
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
        return
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("403", "Forbidden"):
            print(f"Bucket '{bucket}' exists (no list permission — skipping setup).")
            return  # bucket + policy already configured from initial setup
        print(f"Creating bucket '{bucket}' in {region}...")
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
        print("Bucket created.")

    # Allow public bucket policy (ACLs are disabled on new buckets since 2023)
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )

    # Bucket policy granting public read on processed/*
    import json
    policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadProcessed",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket}/processed/*",
        }],
    })
    s3.put_bucket_policy(Bucket=bucket, Policy=policy)


def upload_files(s3, bucket, processed_dir, files):
    base_url = f"https://{bucket}.s3.{REGION}.amazonaws.com"
    print()
    for fname in files:
        local_path = os.path.join(processed_dir, fname)
        s3_key = f"processed/{fname}"
        print(f"Uploading {fname}...")
        s3.upload_file(local_path, bucket, s3_key)
        print(f"  → {base_url}/{s3_key}")
    print("\nDone. Files are live on S3.")


if __name__ == "__main__":
    key_id, secret = load_credentials()
    s3 = get_s3_client(key_id, secret)
    create_bucket(s3, BUCKET, REGION)
    upload_files(s3, BUCKET, PROCESSED_DIR, FILES)
