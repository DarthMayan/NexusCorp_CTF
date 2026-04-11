# NEXUS Corp CTF 🏢🔓

**A multi-level Capture The Flag platform themed as corporate espionage against a corrupt tech corporation.**

Built for the UPMX Ethical Hacking course. 6 levels of escalating difficulty covering brute-force attacks, SQL injection, hash cracking, SSH exploration, LDAP enumeration, and vault breaching.

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
| 6 | CEO Vault | Final authentication | Hash cracking + login |

**Flag format:** `NEXUS{...}`

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
docker compose up --build -d
```

The platform will be available at `http://localhost:5000`

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
│       ├── dashboard.html      # Team progress dashboard
│       ├── scoreboard.html     # Live rankings
│       └── levels/
│           ├── level1.html     # Employee Portal
│           ├── level2.html     # HR Database (SQLi)
│           ├── level3.html     # Hash Cracking
│           ├── level4.html     # SSH Terminal
│           ├── level5.html     # LDAP Search
│           └── level6.html     # CEO Vault
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
- **ceo_vault** — Classified documents with the final flag

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
5. Add the level card to `dashboard.html`
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
