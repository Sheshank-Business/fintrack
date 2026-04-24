"""
auth.py — Fintrack Multi-User Authentication

PIN-based login system:
- PIN entered ONCE per browser session (fast UX)
- Each user sees only their own data
- URL shortcut: ?user=shanky pre-fills the username
- PINs stored as SHA256 hash (never plain text)
"""

import streamlit as st
import hashlib
from datetime import datetime


# ─── Helpers ────────────────────────────────────────────────────
def hash_pin(pin: str) -> str:
    """SHA256 hash a PIN string."""
    return hashlib.sha256(pin.strip().encode()).hexdigest()


def is_logged_in() -> bool:
    return bool(st.session_state.get("ft_user"))


def get_current_user() -> str:
    """Return logged-in username or empty string."""
    return st.session_state.get("ft_user", "")


def logout():
    st.session_state.pop("ft_user", None)
    st.session_state.pop("ft_user_name", None)
    st.rerun()


# ─── Login Screen ───────────────────────────────────────────────
def show_login(db):
    """Show the login/signup screen. Blocks until user logs in."""

    # Pre-fill from URL ?user=shanky
    query_user = st.query_params.get("user", "")

    st.markdown("""
        <style>
        .login-box {
            max-width: 420px;
            margin: 2rem auto;
            background: rgba(108,99,255,0.07);
            border: 1px solid rgba(108,99,255,0.2);
            border-radius: 20px;
            padding: 2.5rem 2rem;
        }
        .login-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg,#6C63FF,#C084FC,#F472B6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin-bottom: .25rem;
        }
        .login-sub {
            text-align: center;
            color: #9BA1B0;
            font-size: .9rem;
            margin-bottom: 1.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-title">💰 Fintrack</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Your personal finance OS</div>', unsafe_allow_html=True)
    st.markdown("---")

    login_tab, signup_tab = st.tabs(["🔑 Login", "👤 Create Profile"])

    # ── LOGIN ──────────────────────────────────────────────────
    with login_tab:
        existing_users = db.get_all_users()
        usernames = [u["username"] for u in existing_users]

        if not usernames:
            st.info("No profiles yet. Create one in the 'Create Profile' tab →")
        else:
            with st.form("login_form", clear_on_submit=False):
                # Pre-fill from URL param
                default_idx = 0
                if query_user in usernames:
                    default_idx = usernames.index(query_user)

                sel_user = st.selectbox(
                    "👤 Select Profile",
                    options=usernames,
                    index=default_idx,
                    format_func=lambda u: next(
                        (x["name"] for x in existing_users if x["username"] == u), u
                    ),
                )
                pin_input = st.text_input(
                    "🔐 Enter PIN",
                    type="password",
                    max_chars=6,
                    placeholder="4-6 digit PIN",
                )
                login_btn = st.form_submit_button("→ Login", use_container_width=True, type="primary")

            if login_btn:
                if not pin_input.strip():
                    st.error("Please enter your PIN.")
                else:
                    user_data = next((u for u in existing_users if u["username"] == sel_user), None)
                    if user_data and user_data["pin_hash"] == hash_pin(pin_input):
                        st.session_state["ft_user"]      = sel_user
                        st.session_state["ft_user_name"] = user_data["name"]
                        st.rerun()
                    else:
                        st.error("❌ Wrong PIN. Try again.")

            # URL shortcuts
            if usernames:
                st.markdown("---")
                st.markdown("**📲 Quick links (bookmark on phone):**")
                app_url = "https://fintrack-dnqyqec9hfpdehyum3vmkh.streamlit.app"
                for u in existing_users:
                    st.markdown(
                        f"`{app_url}?user={u['username']}` — {u['name']}",
                    )

    # ── SIGNUP ────────────────────────────────────────────────
    with signup_tab:
        with st.form("signup_form", clear_on_submit=True):
            new_name     = st.text_input("Your Name",     placeholder="e.g. Shanky")
            new_username = st.text_input("Username",       placeholder="e.g. shanky  (no spaces)")
            new_pin      = st.text_input("Create PIN (4-6 digits)", type="password", max_chars=6)
            new_pin2     = st.text_input("Confirm PIN",   type="password", max_chars=6)
            create_btn   = st.form_submit_button("✅ Create Profile", use_container_width=True, type="primary")

        if create_btn:
            errs = []
            if not new_name.strip():        errs.append("Name is required.")
            if not new_username.strip():    errs.append("Username is required.")
            if " " in new_username.strip(): errs.append("Username cannot have spaces.")
            if len(new_pin) < 4:            errs.append("PIN must be at least 4 digits.")
            if new_pin != new_pin2:         errs.append("PINs don't match.")
            existing_users2 = db.get_all_users()
            if any(u["username"] == new_username.strip().lower() for u in existing_users2):
                errs.append("Username already taken.")

            if errs:
                for e in errs:
                    st.error(e)
            else:
                db.create_user(
                    username  = new_username.strip().lower(),
                    name      = new_name.strip(),
                    pin_hash  = hash_pin(new_pin),
                )
                st.session_state["ft_user"]      = new_username.strip().lower()
                st.session_state["ft_user_name"] = new_name.strip()
                st.success(f"Welcome, {new_name}! 🎉")
                st.rerun()

    st.markdown(
        "<div style='text-align:center;color:#9BA1B0;font-size:0.75rem;margin-top:2rem;'>"
        "💰 Fintrack · Your data, your control</div>",
        unsafe_allow_html=True,
    )
