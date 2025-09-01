import os
import re
from datetime import datetime
from upload_to_wasabi import s3_client, WASABI_BUCKET_NAME  # reuse your existing setup

# -- Company map
COMPANY_CODE_MAP = {
    'HERITAGE': 'heritage',
    'METRO': 'metro',
    'TRISTATE': 'tristate',
}

def extract_company_code(subject):
    match = re.search(r'\[([A-Z0-9_]+)\]', subject)
    if match:
        return COMPANY_CODE_MAP.get(match.group(1).upper())
    return None

def log_upload(sender_email, subject, wasabi_key, file_path):
    log_line = f"{datetime.now()},{sender_email},{subject},{wasabi_key},{file_path}\n"
    os.makedirs("logs", exist_ok=True)
    with open("logs/upload_log.csv", "a") as f:
        f.write(log_line)

def process_email_attachment(file_path, subject, sender_email, fallback_dir="_unassigned"):
    company_folder = extract_company_code(subject)
    if not company_folder:
        print(f"⚠️ Company code not found in subject: {subject}")
        company_folder = fallback_dir

    filename = os.path.basename(file_path)
    key_name = f"data/uploads/{company_folder}/incoming/{filename}"

    try:
        s3_client.upload_file(file_path, WASABI_BUCKET_NAME, key_name)
        print(f"✅ Uploaded to Wasabi: {key_name}")
        log_upload(sender_email, subject, key_name, file_path)
        return key_name
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None
