"""
create_sheet.py — Auto-creates a Google Sheet for Fintrack
Run once: python create_sheet.py
"""
import json
import sys
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Installing gspread...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "gspread", "google-auth"], check=True)
    import gspread
    from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SA_FILE = Path(__file__).parent / "service_account.json"
SECRET_FILE = Path(__file__).parent / ".streamlit" / "secrets.toml"

# Load service account
with open(SA_FILE, encoding="utf-8") as f:
    sa_info = json.load(f)

creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
client = gspread.authorize(creds)

print("[OK] Authenticated with Google")

# Create new spreadsheet
sh = client.create("Fintrack - Finance OS")
print(f"[OK] Created spreadsheet: {sh.title}")
print(f"     Sheet ID: {sh.id}")
print(f"     URL: https://docs.google.com/spreadsheets/d/{sh.id}/edit")

# Share with owner email
OWNER_EMAIL = "kr.sheshank230898@gmail.com"
sh.share(OWNER_EMAIL, perm_type="user", role="owner", notify=False)
print(f"[OK] Shared with {OWNER_EMAIL} as owner")

# Set up initial worksheets with headers
ws_txn = sh.sheet1
ws_txn.update_title("Transactions")
ws_txn.append_row(["Date", "Category", "Amount", "Type", "Note"])

ws_budget = sh.add_worksheet(title="Budget", rows=100, cols=2)
ws_budget.append_row(["Month", "Budget"])

ws_config = sh.add_worksheet(title="Config", rows=100, cols=2)
ws_config.append_row(["Key", "Value"])

print("[OK] Created worksheets: Transactions, Budget, Config")

# Update secrets.toml with new Sheet ID
secrets_content = SECRET_FILE.read_text(encoding="utf-8")
import re
updated = re.sub(
    r'spreadsheet_id\s*=\s*"[^"]*"',
    f'spreadsheet_id = "{sh.id}"',
    secrets_content
)
SECRET_FILE.write_text(updated, encoding="utf-8")
print("[OK] Updated .streamlit/secrets.toml with new Sheet ID")

print("\n" + "="*60)
print("DONE! Your Google Sheet is ready.")
print(f"Sheet ID: {sh.id}")
print(f"Open: https://docs.google.com/spreadsheets/d/{sh.id}/edit")
print("="*60)
print("\nIMPORTANT: Copy this line to Streamlit Cloud secrets:")
print(f'    spreadsheet_id = "{sh.id}"')

