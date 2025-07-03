import os
from imap_tools import MailBox, AND
from dotenv import load_dotenv
from datetime import datetime

# Load credentials from .env
load_dotenv()  # Keep this relative to your working dir
EMAIL = os.getenv("Z_EMAIL")
PASSWORD = os.getenv("Z_PASSWORD")

SAVE_DIR = './data/uploads'
os.makedirs(SAVE_DIR, exist_ok=True)

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
            # Optional post-processing
            # mailbox.move(msg.uid, 'Processed')  # or mailbox.flag(msg.uid, SEEN=True)

if __name__ == "__main__":
    run()
