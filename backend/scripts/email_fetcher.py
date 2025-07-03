import os
from imap_tools import MailBox, AND
from dotenv import load_dotenv
from datetime import datetime
import boto3

# Load .env
load_dotenv()
EMAIL = os.getenv("Z_EMAIL")
PASSWORD = os.getenv("Z_PASSWORD")

# Wasabi config
WASABI_BUCKET = os.getenv("WASABI_BUCKET_NAME")
WASABI_ENDPOINT = os.getenv("WASABI_ENDPOINT")
WASABI_REGION = os.getenv("WASABI_REGION")
WASABI_ACCESS_KEY = os.getenv("WASABI_ACCESS_KEY")
WASABI_SECRET_KEY = os.getenv("WASABI_SECRET_KEY")

SAVE_DIR = './data/uploads'
os.makedirs(SAVE_DIR, exist_ok=True)

# Init Wasabi S3 client
s3 = boto3.client(
    's3',
    endpoint_url=WASABI_ENDPOINT,
    aws_access_key_id=WASABI_ACCESS_KEY,
    aws_secret_access_key=WASABI_SECRET_KEY,
    region_name=WASABI_REGION,
)

def upload_to_wasabi(filepath, filename):
    try:
        s3.upload_file(filepath, WASABI_BUCKET, f"data/uploads/{filename}")
        print(f"📤 Uploaded {filename} to Wasabi bucket: {WASABI_BUCKET}")
    except Exception as e:
        print(f"❌ Failed to upload {filename} to Wasabi:", str(e))

def run():
    print(f"[{datetime.now()}] Connecting to Zoho IMAP...")
    print(f"Testing IMAP login with:\n  EMAIL = {EMAIL}\n  PASSWORD = {'*' * len(PASSWORD) if PASSWORD else 'None'}")

    with MailBox('imap.zoho.com').login(EMAIL, PASSWORD, initial_folder='IMPORT') as mailbox:
        for msg in mailbox.fetch(AND(seen=False), reverse=True):
            print(f"📧 From: {msg.from_} | Subject: {msg.subject}")
            for att in msg.attachments:
                if att.filename.endswith('.csv'):
                    filepath = os.path.join(SAVE_DIR, att.filename)
                    with open(filepath, 'wb') as f:
                        f.write(att.payload)
                    print(f"✅ Saved: {att.filename} → {filepath}")
                    upload_to_wasabi(filepath, att.filename)
            # ✅ Move processed email inside loop
            mailbox.move(msg.uid, 'PROCESSED')
            print(f"📦 Moved message UID {msg.uid} to 'PROCESSED'")


if __name__ == "__main__":
    run()
