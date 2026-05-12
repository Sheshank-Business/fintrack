# Fintrack User Manual (Supabase + Flexible Sign-In)

This manual explains exactly how you and other users can use Fintrack from any device (phone, laptop, tablet) with secure, separate data.

## 1. What You Get

- One shared app URL, usable from any browser.
- Flexible sign-in: Google OAuth or family login (name + passcode / name-only).
- Each user sees only their own transactions and budgets.
- Same account can be used on phone and laptop simultaneously.

## 2. How Login Works (Important)

- First time on a device: user logs in once using the selected auth mode.
- After login: user stays logged in on that device/browser.
- User does not need to log in every time.
- Explicit logout is required to end session on that device.

## 3. Choose Auth Mode

You can use one of these modes in secrets:

- passcode: each person enters name + shared family passcode
- name_only: each person enters only name
- google: Google OAuth sign-in

Example:

```toml
[app_auth]
mode = "passcode"   # or "name_only" or "google"
shared_passcode = "1234"
admin_user = "Shanky"   # Optional: set who can see all family data
```

If using passcode or name_only, Google OAuth setup is not required.

## 4. One-Time Owner Setup

### Step 1: Create Supabase project

1. Go to https://supabase.com.
2. Create a new project (example: fintrack).
3. Open Settings -> API.
4. Copy:
- Project URL
- anon public key

### Step 2: Create database tables

Run this SQL in Supabase SQL Editor:

```sql
create extension if not exists pgcrypto;

create table if not exists transactions (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,
  date date not null,
  type text not null,
  category text not null,
  amount numeric not null,
  note text default '',
  created_at timestamp default now()
);

create table if not exists budgets (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,
  month text not null,
  amount numeric not null,
  unique(user_id, month)
);

create table if not exists category_limits (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,
  category text not null,
  amount numeric not null,
  unique(user_id, category)
);

create table if not exists configs (
  id uuid default gen_random_uuid() primary key,
  key text not null unique,
  value text not null default ''
);
```

### Step 3: Configure Streamlit secrets

Use the template in [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example).

For local dev, set these in your [.streamlit/secrets.toml](.streamlit/secrets.toml).
For Streamlit Cloud, paste the same keys in App Settings -> Secrets.

Minimum required sections (passcode mode):

```toml
[supabase]
url = "https://YOUR_PROJECT_REF.supabase.co"
key = "YOUR_SUPABASE_ANON_KEY"

[app_auth]
mode = "passcode"
shared_passcode = "1234"
```

For Google OAuth mode only:

```toml
[auth]
redirect_uri = "https://YOUR-APP-NAME.streamlit.app/oauth2callback"

[google_oauth]
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
```

### Step 4: Deploy app

1. Push code to GitHub.
2. Create app on Streamlit Community Cloud.
3. Set secrets in Streamlit Cloud.
4. Open app URL and test login.

## 5. Daily Usage (Owner)

1. Open your Streamlit app URL.
2. Sign in once with selected mode.
3. Set monthly budget.
4. Add expenses/investments.
5. View dashboard, history, analytics.
6. Optional: set category limits and alert threshold.

## 6. Daily Usage (Other Users)

Any friend/team member can use the same app URL:

1. Open the app URL.
2. Log in with selected mode:
  - passcode: their name + family passcode
  - name_only: their name only
  - google: their Google account
3. Use app normally.

Data isolation behavior:

- Your rows are tagged with your email as user_id (Google) or your name (passcode/name_only).
- Their rows are tagged with their email/name as user_id.
- Queries are always filtered by current logged-in user.
- They cannot see your records in app views.

**Note:** If an admin is configured, the admin user sees all family data in the "👑 Admin" tab.

## 6.5. Admin Features (Optional)

If your family wants one person to oversee all spending:

1. Set `admin_user` in secrets (must match their login name):

```toml
[app_auth]
mode = "passcode"
shared_passcode = "1234"
admin_user = "Shanky"
```

2. When "Shanky" logs in, they see:
   - **👑 Admin tab** with family summary
   - Individual member data (expenses, investments, budgets)
   - All transactions across all family members
   - Monthly spending trends for each member

3. Other family members see no admin features—their normal tabs remain unchanged.

4. Non-admin members cannot see each other's data, only their own.

## 7. Multi-Device Behavior

### Same user on phone + laptop

- Sign in once on phone, once on laptop.
- Both sessions remain logged in.
- Data syncs through Supabase instantly.
- Add expense on phone -> visible on laptop after refresh/rerun.

### Different users on different devices

- Each logs in with own Google account.
- Each sees only personal data.

## 8. Running Locally

From project root:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Modes:

- If [supabase] secrets exist -> cloud mode (Supabase + selected sign-in mode).
- If missing -> local JSON fallback mode.

## 9. Logout and Session Control

- Use Logout button in sidebar to sign out of the app session.
- Sign-out is device/browser specific.
- Signing out on phone does not sign out laptop automatically.

## 10. Common Troubleshooting

### App keeps using local mode

- Check [supabase] section in secrets.
- Ensure url and key are present and valid.

### Login screen not working

- If mode = passcode, ensure [app_auth].shared_passcode exists.
- If mode = google, validate [auth] redirect_uri matches deployed app URL.
- If mode = google, check [google_oauth] client_id/client_secret are correct.

### Data not saving

- Verify tables exist in Supabase.
- Confirm anon key is correct.
- Check Supabase project is active (not paused).

### User cannot see expected data

- Ensure they are logged in with intended Google account.
- Data is separated by email; switching account changes dataset.

## 11. Security Notes

- Never commit real secrets to git.
- Keep anon key (and OAuth secret if used) in Streamlit secrets only.
- user_id is based on login identity:
  - google mode: email
  - passcode/name_only mode: normalized name
- **Admin user:** Only set `admin_user` if you trust that person to see all family data. The admin cannot modify other users' data, only view it.
- **Shared passcode:** All family members with the same passcode are equally trusted—anyone can see any other member's data if they manually edit the secrets file. This is by design for family use.

## 12. Quick Share Instructions (for new users)

Send this to any user:

1. Open this link: YOUR_APP_URL
2. Log in with the method shown on screen.
3. Start using Fintrack.
4. Your data is private to your account.

That is it.
