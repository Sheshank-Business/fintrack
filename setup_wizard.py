"""
setup_wizard.py — Fintrack Onboarding

Shows a beautiful setup screen so ANY user (non-technical) can:
1. Use the app immediately with local storage (zero setup)
2. Connect their own Google Sheet by pasting the JSON key in the UI

No file editing required. Everything through the browser UI.
"""

import streamlit as st
import json
import os
from pathlib import Path

SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"
SETUP_DONE_KEY = "setup_complete"


def is_setup_complete() -> bool:
    """
    Returns True if the app is already configured.
    Configured = either:
    - User chose local mode (flag stored in session)
    - secrets.toml already has valid gcp_service_account
    """
    # Already chosen in this session
    if st.session_state.get(SETUP_DONE_KEY):
        return True

    # secrets.toml exists with real credentials
    try:
        creds = st.secrets.get("gcp_service_account", {})
        if creds.get("project_id") and creds.get("private_key"):
            return True
    except Exception:
        pass

    return False


def save_secrets(json_key: dict, sheet_id: str) -> bool:
    """Write credentials to .streamlit/secrets.toml."""
    try:
        SECRETS_PATH.parent.mkdir(exist_ok=True)
        toml_content = f'''[gcp_service_account]
type = "service_account"
project_id = "{json_key.get("project_id", "")}"
private_key_id = "{json_key.get("private_key_id", "")}"
private_key = """{json_key.get("private_key", "")}"""
client_email = "{json_key.get("client_email", "")}"
client_id = "{json_key.get("client_id", "")}"
auth_uri = "{json_key.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")}"
token_uri = "{json_key.get("token_uri", "https://oauth2.googleapis.com/token")}"
auth_provider_x509_cert_url = "{json_key.get("auth_provider_x509_cert_url", "")}"
client_x509_cert_url = "{json_key.get("client_x509_cert_url", "")}"
universe_domain = "googleapis.com"

[sheets]
spreadsheet_id = "{sheet_id}"
'''
        with open(SECRETS_PATH, "w", encoding="utf-8") as f:
            f.write(toml_content)
        return True
    except Exception as e:
        st.error(f"Could not save config: {e}")
        return False


def show_wizard():
    """Render the full onboarding wizard UI."""
    st.markdown("""
        <style>
        .wizard-hero {
            text-align: center;
            padding: 3rem 1rem 1rem;
        }
        .wizard-title {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #6C63FF, #C084FC, #F472B6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }
        .wizard-sub {
            color: #9BA1B0;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }
        .step-card {
            background: rgba(108,99,255,0.08);
            border: 1px solid rgba(108,99,255,0.25);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 0.5rem 0;
        }
        .step-num {
            font-size: 0.75rem;
            font-weight: 700;
            color: #6C63FF;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.25rem;
        }
        .feature-pill {
            display: inline-block;
            background: rgba(108,99,255,0.15);
            border: 1px solid rgba(108,99,255,0.3);
            border-radius: 20px;
            padding: 4px 14px;
            font-size: 0.8rem;
            color: #A78BFA;
            margin: 3px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Hero
    st.markdown("""
        <div class="wizard-hero">
            <div class="wizard-title">💰 Fintrack</div>
            <div class="wizard-sub">Your personal finance OS — track expenses, investments & budgets</div>
            <div>
                <span class="feature-pill">📊 Real-time dashboard</span>
                <span class="feature-pill">📱 Works on phone</span>
                <span class="feature-pill">🎯 Budget alerts</span>
                <span class="feature-pill">📈 Analytics</span>
                <span class="feature-pill">💸 ₹0 cost</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🚀 Choose how to store your data")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
            <div class="step-card">
                <div class="step-num">Option 1 — Instant Start</div>
                <h3 style="margin:0.5rem 0;">💾 Local Storage</h3>
                <p style="color:#9BA1B0;font-size:0.9rem;">
                    Data saved on <b>this device</b> only.<br>
                    Zero setup. Works offline.<br>
                    <span style="color:#FFD740;">⚠️ Data stays on this computer.</span>
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("▶️ Start with Local Storage", use_container_width=True, key="local_mode_btn"):
            st.session_state[SETUP_DONE_KEY] = True
            st.session_state["db_mode_chosen"] = "local"
            st.rerun()

    with col2:
        st.markdown("""
            <div class="step-card">
                <div class="step-num">Option 2 — Recommended</div>
                <h3 style="margin:0.5rem 0;">☁️ Google Sheets</h3>
                <p style="color:#9BA1B0;font-size:0.9rem;">
                    Data saved in <b>your own Google Sheet</b>.<br>
                    Access from phone, laptop, anywhere.<br>
                    <span style="color:#34D399;">✅ Free. Your data. Your control.</span>
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🔗 Connect Google Sheets", use_container_width=True,
                     key="sheets_mode_btn", type="primary"):
            st.session_state["show_sheets_setup"] = True
            st.rerun()

    # Google Sheets setup form
    if st.session_state.get("show_sheets_setup"):
        st.markdown("---")
        st.markdown("### 🔑 Connect Your Google Sheet")
        st.caption("Takes about 5 minutes. Free forever. Your data never touches our servers.")

        with st.expander("📋 Step-by-step guide (click to expand)", expanded=False):
            st.markdown("""
**Step 1 — Create a Google Sheet**
- Go to [sheets.new](https://sheets.new)
- Name it **"Fintrack"**
- Copy the ID from the URL: `docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`

**Step 2 — Enable Google APIs**
- Go to [console.cloud.google.com](https://console.cloud.google.com)
- Create a project → Enable **Google Sheets API** + **Google Drive API**

**Step 3 — Create a Service Account**
- Go to **IAM & Admin → Service Accounts → Create**
- Name: `fintrack-app` → Click **Done**
- Click the account → **Keys → Add Key → Create new key → JSON**
- This downloads a `.json` file

**Step 4 — Share your Sheet**
- Open your Google Sheet → Click **Share**
- Add the service account email (from the JSON file) as **Editor**

**Step 5 — Paste below ↓**
            """)

        tab_paste, tab_upload = st.tabs(["📋 Paste JSON Key", "📁 Upload JSON File"])

        json_key_dict = None
        sheet_id_input = ""

        with tab_paste:
            st.markdown("Paste the **full contents** of your downloaded JSON key file:")
            json_text = st.text_area(
                "JSON Key Content",
                height=200,
                placeholder='{\n  "type": "service_account",\n  "project_id": "your-project",\n  ...\n}',
                key="json_paste_input",
                label_visibility="collapsed",
            )
            if json_text.strip():
                try:
                    json_key_dict = json.loads(json_text.strip())
                    st.success(f"✅ Valid JSON detected! Project: `{json_key_dict.get('project_id', '?')}`")
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON — make sure you paste the complete file contents.")

        with tab_upload:
            uploaded = st.file_uploader("Upload your JSON key file", type=["json"], key="json_upload")
            if uploaded:
                try:
                    json_key_dict = json.load(uploaded)
                    st.success(f"✅ File loaded! Project: `{json_key_dict.get('project_id', '?')}`")
                except Exception:
                    st.error("❌ Could not read the file. Make sure it's the correct JSON key file.")

        st.markdown("**Your Google Sheet ID:**")
        sheet_id_input = st.text_input(
            "Sheet ID",
            placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
            help="Found in your Google Sheet URL: docs.google.com/spreadsheets/d/[THIS PART]/edit",
            label_visibility="collapsed",
            key="sheet_id_input",
        )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button(
                "💾 Save & Connect",
                use_container_width=True,
                type="primary",
                disabled=(json_key_dict is None or not sheet_id_input.strip()),
                key="save_sheets_btn",
            ):
                with st.spinner("Connecting to Google Sheets..."):
                    if save_secrets(json_key_dict, sheet_id_input.strip()):
                        # Test connection
                        try:
                            import gspread
                            from google.oauth2.service_account import Credentials
                            creds = Credentials.from_service_account_info(
                                json_key_dict,
                                scopes=[
                                    "https://www.googleapis.com/auth/spreadsheets",
                                    "https://www.googleapis.com/auth/drive",
                                ]
                            )
                            client = gspread.authorize(creds)
                            client.open_by_key(sheet_id_input.strip())
                            st.success("🎉 Connected successfully! Restarting app...")
                            st.session_state[SETUP_DONE_KEY] = True
                            st.session_state["db_mode_chosen"] = "sheets"
                            st.rerun()
                        except gspread.SpreadsheetNotFound:
                            st.error("❌ Sheet not found! Did you share it with the service account email?")
                            st.code(json_key_dict.get("client_email", ""), language=None)
                        except Exception as e:
                            st.error(f"❌ Connection failed: {e}")
                            st.info("💡 Tip: Make sure you shared the sheet with the service account email.")

        with btn_col2:
            if st.button("← Back", use_container_width=True, key="back_btn"):
                st.session_state["show_sheets_setup"] = False
                st.rerun()

        if json_key_dict:
            st.markdown("---")
            st.info(f"📧 **Share your Google Sheet with:** `{json_key_dict.get('client_email', '')}`")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:#9BA1B0;font-size:0.8rem;'>"
        "💰 Fintrack · Free forever · Your data stays with you"
        "</div>",
        unsafe_allow_html=True,
    )
