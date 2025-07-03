import boto3
import os
from dotenv import load_dotenv

load_dotenv()

WASABI_ACCESS_KEY = os.getenv('WASABI_ACCESS_KEY')
WASABI_SECRET_KEY = os.getenv('WASABI_SECRET_KEY')
WASABI_BUCKET_NAME = os.getenv('WASABI_BUCKET_NAME')
WASABI_REGION = os.getenv('WASABI_REGION', 'us-east-1')  # default region
WASABI_ENDPOINT = os.getenv('WASABI_ENDPOINT', 'https://s3.wasabisys.com')

s3_client = boto3.client(
    's3',
    aws_access_key_id=WASABI_ACCESS_KEY,
    aws_secret_access_key=WASABI_SECRET_KEY,
    endpoint_url=WASABI_ENDPOINT,
    region_name=WASABI_REGION
)

def upload_file_to_wasabi(file_path, key_name=None):
    if not key_name:
        key_name = os.path.basename(file_path)

    try:
        s3_client.upload_file(file_path, WASABI_BUCKET_NAME, key_name)
        print(f"✅ Uploaded {file_path} to Wasabi as {key_name}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
