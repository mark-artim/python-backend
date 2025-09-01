import os
import re
from datetime import datetime, timedelta
from io import BytesIO
from PyPDF2 import PdfReader
import requests
import boto3
from pymongo import MongoClient
from dotenv import load_dotenv
print("📁 check_transfers.py loaded and .env applied")

load_dotenv()

# --- ENV VARS
WASABI_ACCESS_KEY = os.getenv("WASABI_ACCESS_KEY")
WASABI_SECRET_KEY = os.getenv("WASABI_SECRET_KEY")
WASABI_BUCKET_NAME = os.getenv("WASABI_BUCKET_NAME")
WASABI_ENDPOINT = os.getenv("WASABI_ENDPOINT", "https://s3.wasabisys.com")
WASABI_REGION = os.getenv("WASABI_REGION", "us-east-1")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")
DEFAULT_ALERT_EMAIL = "mark.artim@heritagedistribution.com"

# --- SETUP
s3 = boto3.client(
    's3',
    aws_access_key_id=WASABI_ACCESS_KEY,
    aws_secret_access_key=WASABI_SECRET_KEY,
    endpoint_url=WASABI_ENDPOINT,
    region_name=WASABI_REGION
)

# --- Mongo connection
def get_active_companies():
    client = MongoClient(MONGO_URI)
    db = client["emp54"]
    companies = db.companies.find({})
    
    result = []
    for company in companies:
        result.append({
            "name": company.get("name"),
            "code": company.get("companyCode"),
            "wasabiPrefix": company.get("wasabiPrefix", company.get("companyCode")),
            "alertEmail": company.get("alertEmail", DEFAULT_ALERT_EMAIL)
        })
    return result

# --- Wasabi file listing
def get_matching_pdfs(company_prefix):
    prefix = f"data/uploads/{company_prefix}/incoming/"
    response = s3.list_objects_v2(Bucket=WASABI_BUCKET_NAME, Prefix=prefix)
    pdfs = []

    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.lower().endswith(".pdf") and "OrderChangeLog" in key:
            pdfs.append(key)
    print(f"📂 Wasabi found {len(pdfs)} matching PDFs in: {prefix}")
    return pdfs

# --- PDF content reading
def read_pdf_from_wasabi(key):
    pdf_obj = s3.get_object(Bucket=WASABI_BUCKET_NAME, Key=key)
    pdf_bytes = pdf_obj["Body"].read()
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)

# --- Transfer row detection
def extract_recent_transfer_failures(text, window_minutes=60):
    pattern = re.compile(
        r"(?P<date>\d{2}/\d{2}/\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<user_id>\S+)\s+(?P<order_num>T\d+)\s+(?P<details>Attempted to Print.+?)(?=\n\d{2}/\d{2}/\d{2}|\Z)",
        re.DOTALL
    )

    now = datetime.now()
    results = []

    for match in pattern.finditer(text):
        dt_str = f"{match.group('date')} {match.group('time')}"
        timestamp = datetime.strptime(dt_str, "%m/%d/%y %H:%M:%S")
        if timedelta(minutes=0) <= now - timestamp <= timedelta(minutes=window_minutes):
            results.append(match.group(0).strip())

    print(f"🔎 Found {len(results)} recent transfer rows")
    return results

# --- Email alert
def send_resend_email(body, to_email):
    print(f"📧 Sending alert email to {to_email} with {len(body.splitlines())} lines")
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "from": "alerts@emp54.com",
            "to": [to_email],
            "subject": "TRANSFER PRINT ISSUE",
            "text": f"A transfer may not have printed. Please review.\n\n{body}"
        }
    )
    if response.ok:
        print(f"📧 Alert sent to {to_email}")
    else:
        print(f"❌ Failed to send email: {response.text}")

# --- Move scanned file to processed/
def move_to_processed(company_prefix, key):
    filename = key.split("/")[-1]
    new_key = f"data/uploads/{company_prefix}/processed/{filename}"
    s3.copy_object(Bucket=WASABI_BUCKET_NAME, CopySource={"Bucket": WASABI_BUCKET_NAME, "Key": key}, Key=new_key)
    s3.delete_object(Bucket=WASABI_BUCKET_NAME, Key=key)
    print(f"📁 Moved to: {new_key}")

# --- Main scan loop
def run_check():
    print("🧪 Inside run_check()")
    for company in get_active_companies():
        print(f"🏢 Found {len(companies)} companies in MongoDB")
        prefix = company["wasabiPrefix"]
        alert_email = company["alertEmail"]
        print(f"\n🔍 Checking: {company['name']} ({prefix})")

        pdf_keys = get_matching_pdfs(prefix)
        print(f"📂 Found {len(pdf_keys)} PDF(s) in {prefix}")

        for key in pdf_keys:
            print(f"📄 Scanning file: {key}")
            text = read_pdf_from_wasabi(key)
            failures = extract_recent_transfer_failures(text)
            print(f"🔎 Found {len(failures)} transfer failures in {key}")

            if failures:
                send_resend_email("\n\n".join(failures), alert_email)
            else:
                print("✅ No recent transfer failures.")

            move_to_processed(prefix, key)

if __name__ == "__main__":
    print("🚀 Starting transfer scan...")
    run_check()
