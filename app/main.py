"""
NEXUS Corp CTF - Main Application
A multi-level cybersecurity Capture The Flag challenge
themed as corporate espionage against a corrupt tech corporation.

Stack: Flask + Gunicorn + SQLite + Docker
Designed to handle concurrent attack traffic without crashing.
"""

import os
import sqlite3
import hashlib
import logging
import time
from functools import wraps
from datetime import timedelta
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, g, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "NEXUS_CTF_d3v_k3y_ch4ng3_m3!")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=4)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("nexus_ctf")

# ---------------------------------------------------------------------------
# Rate limiter  (in-memory, per-IP, thread-safe enough for gunicorn --preload)
# ---------------------------------------------------------------------------
_rate_store: dict[str, list[float]] = {}
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", 60))       # requests
RATE_WINDOW = int(os.environ.get("RATE_WINDOW", 60))      # seconds

RATE_LIMIT_FUZZ = int(os.environ.get("RATE_LIMIT_FUZZ", 300))

def rate_limited(limit=None):
    """Return True if the caller should be throttled."""
    if limit is None:
        limit = RATE_LIMIT
    ip = request.remote_addr or "unknown"
    now = time.time()
    hits = _rate_store.setdefault(ip, [])
    hits[:] = [t for t in hits if now - t < RATE_WINDOW]
    if len(hits) >= limit:
        return True
    hits.append(now)
    return False

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MAIN_DB = os.path.join(DB_DIR, "nexus_main.db")
VULN_DB = os.path.join(DB_DIR, "nexus_vulnerable.db")  # intentionally injectable

def get_main_db():
    """Safe database – stores CTF progress, teams, flags."""
    if "main_db" not in g:
        g.main_db = sqlite3.connect(MAIN_DB)
        g.main_db.row_factory = sqlite3.Row
    return g.main_db

def get_vuln_db():
    """Vulnerable database – used for SQL injection levels."""
    if "vuln_db" not in g:
        g.vuln_db = sqlite3.connect(VULN_DB)
        g.vuln_db.row_factory = sqlite3.Row
    return g.vuln_db

@app.teardown_appcontext
def close_dbs(exception):
    for key in ("main_db", "vuln_db"):
        db = g.pop(key, None)
        if db:
            db.close()

# ---------------------------------------------------------------------------
# Flags – each level has a unique flag
# ---------------------------------------------------------------------------
FLAGS = {
    1: "NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}",
    2: "NEXUS{sql_1nj3ct10n_m4st3r_9f2d}",
    3: "NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}",
    4: "NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}",
    5: "NEXUS{ld4p_3num3r4t10n_pr0_5d7b}",
    6: "NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}",
}

# ---------------------------------------------------------------------------
# Initialise databases
# ---------------------------------------------------------------------------

def init_databases():
    """Create and seed both databases."""
    os.makedirs(DB_DIR, exist_ok=True)

    # ── MAIN DB (safe) ──────────────────────────────────────────────────
    conn = sqlite3.connect(MAIN_DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            level INTEGER NOT NULL,
            flag_submitted TEXT,
            solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id),
            UNIQUE(team_id, level)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attack_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            endpoint TEXT,
            payload TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    # ── VULNERABLE DB (intentionally insecure) ──────────────────────────
    conn = sqlite3.connect(VULN_DB)
    c = conn.cursor()

    # Level 1: Weak-credential employee portal
    c.execute("""
        CREATE TABLE IF NOT EXISTS portal_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            department TEXT,
            email TEXT
        )
    """)

    # Seed weak credentials (brute-forceable)
    employees = [
        ("admin",      "admin",           "Administrator", "IT",        "admin@nexuscorp.local"),
        ("jsmith",     "password123",     "Employee",      "Sales",     "jsmith@nexuscorp.local"),
        ("mgarcia",    "nexus2024",       "Employee",      "Marketing", "mgarcia@nexuscorp.local"),
        ("cjohnson",   "welcome1",        "Manager",       "Finance",   "cjohnson@nexuscorp.local"),
        ("akim",       "letmein",         "Employee",      "R&D",       "akim@nexuscorp.local"),
        ("root",       "toor",            "SysAdmin",      "IT",        "root@nexuscorp.local"),
        ("dbadmin",    "dbadmin",         "DBA",           "IT",        "dbadmin@nexuscorp.local"),
        ("guest",      "guest",           "Guest",         "Lobby",     "guest@nexuscorp.local"),
    ]
    for emp in employees:
        try:
            c.execute("INSERT INTO portal_users VALUES (NULL,?,?,?,?,?)", emp)
        except sqlite3.IntegrityError:
            pass

    # Level 2: Internal HR database (SQL injection target)
    c.execute("DROP TABLE IF EXISTS hr_employees")
    c.execute("""
        CREATE TABLE hr_employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT,
            full_name TEXT,
            position TEXT,
            salary REAL,
            department TEXT,
            hire_date TEXT
        )
    """)

    hr_data = [
        ("NX-1001", "Elena Voss",       "CEO",                    450000, "Executive",  "2015-03-12"),
        ("NX-1002", "Marcus Chen",      "CTO",                    380000, "Executive",  "2015-06-01"),
        ("NX-1003", "Sarah Mitchell",   "CFO",                    370000, "Executive",  "2016-01-15"),
        ("NX-1004", "David Park",       "VP Engineering",         280000, "Engineering","2016-09-20"),
        ("NX-1005", "Lisa Rodriguez",   "VP Sales",               275000, "Sales",      "2017-02-14"),
        ("NX-1006", "James O'Brien",    "Lead Developer",         185000, "Engineering","2017-08-03"),
        ("NX-1007", "Aisha Patel",      "Security Analyst",       145000, "Security",   "2018-01-22"),
        ("NX-1008", "Tom Wagner",       "Network Admin",          130000, "IT",         "2018-05-10"),
        ("NX-1009", "Nina Kowalski",    "HR Director",            165000, "HR",         "2018-11-30"),
        ("NX-1010", "Carlos Mendez",    "Junior Developer",        95000, "Engineering","2020-03-15"),
        ("NX-1011", "Rebecca Frost",    "Data Analyst",           110000, "Analytics",  "2020-07-01"),
        ("NX-1012", "Kevin Tanaka",     "Sys Admin",              125000, "IT",         "2019-04-18"),
    ]
    for emp in hr_data:
        c.execute("INSERT INTO hr_employees VALUES (NULL,?,?,?,?,?,?)", emp)

    # SECRET table hidden in the DB – players discover it via SQLi
    c.execute("DROP TABLE IF EXISTS ssh_credentials")
    c.execute("""
        CREATE TABLE ssh_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT,
            username TEXT,
            password_hash TEXT,
            notes TEXT,
            flag TEXT
        )
    """)

    # Always wipe and reseed to prevent duplicate rows on each restart
    c.execute("DELETE FROM ssh_credentials")
    ssh_creds = [
        ("nexus-internal-srv", "sysop",  hashlib.md5(b"master").hexdigest(),           "Main server – DO NOT SHARE", FLAGS[2]),
        ("nexus-backup-srv",   "backup", hashlib.md5(b"B4ckup2024").hexdigest(),       "Nightly backup account",     None),
        ("nexus-dev-srv",      "devops", hashlib.sha256(b"D3v0ps#Acc3ss").hexdigest(), "CI/CD pipeline",             None),
    ]
    for cred in ssh_creds:
        c.execute("INSERT INTO ssh_credentials (hostname, username, password_hash, notes, flag) VALUES (?,?,?,?,?)", cred)

    # Level 5: LDAP-style directory (simulated as SQL table)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ldap_directory (
            dn TEXT PRIMARY KEY,
            cn TEXT,
            uid TEXT,
            mail TEXT,
            userPassword TEXT,
            ou TEXT,
            title TEXT,
            clearance_level INTEGER
        )
    """)

    ldap_entries = [
        ("cn=Elena Voss,ou=Executive,dc=nexuscorp,dc=local",
         "Elena Voss", "evoss", "evoss@nexuscorp.local",
         hashlib.sha256(b"V0ss_C30_2024!").hexdigest(),
         "Executive", "CEO", 5),
        ("cn=Marcus Chen,ou=Executive,dc=nexuscorp,dc=local",
         "Marcus Chen", "mchen", "mchen@nexuscorp.local",
         hashlib.sha256(b"Ch3n_CTO#s3cure").hexdigest(),
         "Executive", "CTO", 4),
        ("cn=Security Bot,ou=Security,dc=nexuscorp,dc=local",
         "Security Bot", "secbot", "secbot@nexuscorp.local",
         hashlib.sha256(b"s3cB0t_autom4t10n").hexdigest(),
         "Security", "Automated Scanner", 3),
        ("cn=Vault Access,ou=System,dc=nexuscorp,dc=local",
         "Vault Service", "vault_svc", "vault@nexuscorp.local",
         hashlib.sha256(b"dragon").hexdigest(),
         "System", "Vault Access Service Account", 5),
    ]
    for entry in ldap_entries:
        try:
            c.execute("INSERT INTO ldap_directory VALUES (?,?,?,?,?,?,?,?)", entry)
        except sqlite3.IntegrityError:
            pass

    # Level 6: CEO Vault
    c.execute("DROP TABLE IF EXISTS ceo_vault")
    c.execute("""
        CREATE TABLE ceo_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT,
            classification TEXT,
            content TEXT,
            accessed_by TEXT DEFAULT NULL,
            access_time TIMESTAMP DEFAULT NULL
        )
    """)

    vault_docs = [
        ("Project_Chimera_Financials.pdf",  "TOP SECRET",
         "Offshore accounts routing $47M through shell companies in 3 jurisdictions. "
         "Flag: " + FLAGS[6]),
        ("Board_Meeting_Minutes_Q4.pdf",    "CONFIDENTIAL",
         "Discussion of covering up data breach affecting 2.3M users."),
        ("Operation_Blackout_Plan.docx",    "TOP SECRET",
         "Planned sabotage of competitor infrastructure. Legal has NOT been consulted."),
        ("Employee_Surveillance_Report.xlsx","SECRET",
         "Monitoring employee communications without consent since 2021."),
    ]
    for doc in vault_docs:
        c.execute("INSERT INTO ceo_vault (document_name, classification, content) VALUES (?,?,?)", doc)

    conn.commit()
    conn.close()
    logger.info("Databases initialized and seeded.")


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

@app.before_request
def before_request_handler():
    # Level 1 login is intentionally brute-forceable — skip rate limiting
    if request.path == "/level/1/login":
        pass
    else:
        limit = RATE_LIMIT_FUZZ if request.path.startswith("/level/6/vault-api") else RATE_LIMIT
        if rate_limited(limit):
            return jsonify({"error": "Rate limit exceeded. Try again shortly."}), 429

    # Log attack-relevant requests
    if request.method == "POST" and request.path not in ("/register", "/team-login"):
        try:
            db = get_main_db()
            payload = str(request.form.to_dict()) if request.form else str(request.get_json(silent=True))
            db.execute(
                "INSERT INTO attack_log (ip, endpoint, payload) VALUES (?, ?, ?)",
                (request.remote_addr, request.path, payload[:2000])
            )
            db.commit()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def team_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "team_id" not in session:
            flash("Register or log in with your team first.", "warning")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def get_team_progress(team_id: int) -> set[int]:
    db = get_main_db()
    rows = db.execute("SELECT level FROM progress WHERE team_id = ?", (team_id,)).fetchall()
    return {r["level"] for r in rows}

# ---------------------------------------------------------------------------
# Routes – Public
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("team_name", "").strip()
    pwd = request.form.get("password", "")
    if not name or not pwd:
        flash("Team name and password required.", "error")
        return redirect(url_for("index"))
    db = get_main_db()
    try:
        db.execute(
            "INSERT INTO teams (team_name, password_hash) VALUES (?, ?)",
            (name, generate_password_hash(pwd))
        )
        db.commit()
        row = db.execute("SELECT id FROM teams WHERE team_name = ?", (name,)).fetchone()
        session["team_id"] = row["id"]
        session["team_name"] = name
        session.permanent = True
        flash(f"Team '{name}' registered. Welcome, operative.", "success")
    except sqlite3.IntegrityError:
        flash("Team name already taken.", "error")
    return redirect(url_for("challenges"))


@app.route("/team-login", methods=["POST"])
def team_login():
    name = request.form.get("team_name", "").strip()
    pwd = request.form.get("password", "")
    db = get_main_db()
    row = db.execute("SELECT * FROM teams WHERE team_name = ?", (name,)).fetchone()
    if row and check_password_hash(row["password_hash"], pwd):
        session["team_id"] = row["id"]
        session["team_name"] = row["team_name"]
        session.permanent = True
        return redirect(url_for("challenges"))
    flash("Invalid team credentials.", "error")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Routes – Challenges (level grid) & Scoreboard
# ---------------------------------------------------------------------------

@app.route("/challenges")
@team_required
def challenges():
    solved = get_team_progress(session["team_id"])
    return render_template("dashboard.html",
                           team_name=session["team_name"],
                           solved=solved,
                           total_levels=6,
                           flags=FLAGS)


@app.route("/dashboard")
def dashboard_redirect():
    """Legacy URL — old bookmarks and docs still work."""
    return redirect(url_for("challenges"))


@app.route("/scoreboard")
def scoreboard():
    db = get_main_db()
    teams = db.execute("""
        SELECT t.team_name,
               COUNT(p.level) as levels_solved,
               MAX(p.solved_at) as last_solve
        FROM teams t
        LEFT JOIN progress p ON t.id = p.team_id
        GROUP BY t.id
        ORDER BY levels_solved DESC, last_solve ASC
    """).fetchall()
    return render_template("scoreboard.html", teams=teams)


@app.route("/submit-flag", methods=["POST"])
@team_required
def submit_flag():
    level = request.form.get("level", type=int)
    flag = request.form.get("flag", "").strip()
    if not level or level not in FLAGS:
        return jsonify({"success": False, "message": "Invalid level."}), 400

    if FLAGS.get(level) == flag:
        db = get_main_db()
        try:
            db.execute(
                "INSERT INTO progress (team_id, level, flag_submitted) VALUES (?, ?, ?)",
                (session["team_id"], level, flag)
            )
            db.commit()
            return jsonify({"success": True, "message": f"Level {level} cleared! Access granted to next sector."})
        except sqlite3.IntegrityError:
            return jsonify({"success": True, "message": "Already solved."})
    return jsonify({"success": False, "message": "Incorrect flag. Access denied."}), 403


# ---------------------------------------------------------------------------
# LEVEL 1 – Employee Portal (Weak credentials / Brute-force)
# ---------------------------------------------------------------------------

@app.route("/level/1")
@team_required
def level1():
    return render_template("levels/level1.html",
                           solved=1 in get_team_progress(session["team_id"]))


@app.route("/level/1/login", methods=["POST"])
def level1_login():
    """
    INTENTIONALLY VULNERABLE: No account lockout, no CAPTCHA.
    Designed to be brute-forced with Hydra / Medusa.
    Returns distinguishable success/failure messages for tool parsing.
    """
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    db = get_vuln_db()
    # Intentionally using parameterized query here – the vuln is weak creds, not SQLi
    user = db.execute(
        "SELECT * FROM portal_users WHERE username = ? AND password = ?",
        (username, password)
    ).fetchone()

    if user:
        if user["role"] == "Administrator":
            return jsonify({
                "success": True,
                "message": f"Welcome, {user['username']}. Administrator access granted.",
                "flag": FLAGS[1],
                "hint": "You're in. The HR database at /level/2 has some interesting records..."
            })
        return jsonify({
            "success": True,
            "message": f"Welcome, {user['username']}. Role: {user['role']}. "
                       "But you need Administrator access for the flag."
        })

    return jsonify({"success": False, "message": "Login failed. Invalid credentials."}), 200


# ---------------------------------------------------------------------------
# LEVEL 2 – HR Database (SQL Injection)
# ---------------------------------------------------------------------------

@app.route("/level/2")
@team_required
def level2():
    return render_template("levels/level2.html",
                           solved=2 in get_team_progress(session["team_id"]))


@app.route("/level/2/search", methods=["GET", "POST"])
def level2_search():
    """
    INTENTIONALLY VULNERABLE TO SQL INJECTION.
    Uses string formatting instead of parameterized queries.
    Target for sqlmap / manual SQLi.
    """
    query = ""
    results = []
    error = None

    if request.method == "POST":
        query = request.form.get("search", "")
    elif request.method == "GET":
        query = request.args.get("search", "")

    if query:
        db = get_vuln_db()
        # ⚠️  INTENTIONALLY VULNERABLE – string concatenation
        sql = f"SELECT emp_id, full_name, position, department FROM hr_employees WHERE full_name LIKE '%{query}%' OR department LIKE '%{query}%'"
        try:
            cursor = db.execute(sql)
            results = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            error = str(e)
            logger.warning(f"SQLi attempt: {query} -> {error}")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.args.get("format") == "json":
        return jsonify({"results": results, "error": error, "query": query})

    return render_template("levels/level2.html",
                           results=results,
                           error=error,
                           query=query,
                           solved=2 in get_team_progress(session.get("team_id", 0)))


# ---------------------------------------------------------------------------
# LEVEL 3 – Hash Cracking
# ---------------------------------------------------------------------------

@app.route("/level/3")
@team_required
def level3():
    """
    Players arrive here with hashes found in Level 2's ssh_credentials table.
    They must crack the MD5/SHA256 hashes using hashcat or john.
    Submit the cracked password for sysop to get the flag.
    """
    conn = sqlite3.connect(VULN_DB)
    conn.row_factory = sqlite3.Row
    creds = conn.execute(
        "SELECT id, hostname, username, password_hash, notes FROM ssh_credentials ORDER BY id"
    ).fetchall()
    conn.close()
    return render_template("levels/level3.html",
                           solved=3 in get_team_progress(session["team_id"]),
                           creds=creds)


@app.route("/level/3/verify", methods=["POST"])
@team_required
def level3_verify():
    """Verify cracked password for the sysop account."""
    password = request.form.get("password", "")
    # The MD5 of 'master' should have been found in ssh_credentials table
    if password == "master":
        return jsonify({
            "success": True,
            "flag": FLAGS[3],
            "message": "Password verified! SSH access to nexus-internal-srv as 'sysop' granted.",
            "hint": "Connect to the SSH service at /level/4. Use sysop:master"
        })
    return jsonify({"success": False, "message": "Incorrect password. Keep cracking."}), 403


# ---------------------------------------------------------------------------
# LEVEL 4 – SSH Simulation (File system exploration)
# ---------------------------------------------------------------------------

@app.route("/level/4")
@team_required
def level4():
    return render_template("levels/level4.html",
                           solved=4 in get_team_progress(session["team_id"]))


# Simulated file system for SSH level
SSH_FILESYSTEM = {
    "/": ["home/", "etc/", "var/", "tmp/", "opt/"],
    "/home/": ["sysop/"],
    "/home/sysop/": [".bash_history", ".ssh/", "notes.txt", "maintenance.sh"],
    "/home/sysop/.ssh/": ["authorized_keys", "known_hosts", "id_rsa"],
    "/etc/": ["passwd", "shadow", "nexus/"],
    "/etc/nexus/": ["ldap.conf", "network.conf", "backup.key"],
    "/var/": ["log/"],
    "/var/log/": ["auth.log", "nexus-app.log", "cron.log"],
    "/tmp/": ["debug_dump.txt"],
    "/opt/": ["nexus-tools/"],
    "/opt/nexus-tools/": ["scanner.py", "cleanup.sh"],
}

SSH_FILES = {
    "/home/sysop/.bash_history": (
        "ls -la\n"
        "cat /etc/nexus/ldap.conf\n"
        "ldapsearch -x -H ldap://nexus-ldap-srv -b 'dc=nexuscorp,dc=local'\n"
        "ssh devops@nexus-dev-srv\n"
        "mysql -u dbadmin -p nexus_hr\n"
        "cat /tmp/debug_dump.txt\n"
        "exit\n"
    ),
    "/home/sysop/notes.txt": (
        "== MAINTENANCE NOTES ==\n"
        "- LDAP server at ldap://nexus-ldap-srv:389\n"
        "- Base DN: dc=nexuscorp,dc=local\n"
        "- Anonymous bind ENABLED (security ticket #4471 - pending fix)\n"
        "- CEO vault requires clearance_level >= 5\n"
        "- Vault service account: vault_svc\n\n"
        "TODO: Disable anonymous LDAP bind before audit next month!\n"
    ),
    "/home/sysop/.ssh/id_rsa": (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\n"
        "[TRUNCATED - This key is for nexus-backup-srv only]\n"
        "-----END OPENSSH PRIVATE KEY-----\n"
    ),
    "/home/sysop/.ssh/authorized_keys": "ssh-rsa AAAAB3... sysop@nexus-internal-srv\n",
    "/home/sysop/.ssh/known_hosts": (
        "nexus-internal-srv,10.0.1.10 ssh-rsa AAAAB3...\n"
        "nexus-backup-srv,10.0.1.11 ssh-rsa AAAAB3...\n"
        "nexus-ldap-srv,10.0.1.20 ssh-rsa AAAAB3...\n"
        "nexus-dev-srv,10.0.1.30 ssh-rsa AAAAB3...\n"
    ),
    "/home/sysop/maintenance.sh": (
        "#!/bin/bash\n"
        "# Weekly maintenance script\n"
        "echo 'Running LDAP health check...'\n"
        "ldapsearch -x -H ldap://nexus-ldap-srv -b 'dc=nexuscorp,dc=local' '(objectClass=*)'\n"
        "echo 'Checking vault service...'\n"
        "curl -s http://localhost:8443/vault/status\n"
    ),
    "/etc/passwd": (
        "root:x:0:0:root:/root:/bin/bash\n"
        "sysop:x:1001:1001:System Operator:/home/sysop:/bin/bash\n"
        "nexus-svc:x:1002:1002:Nexus Service:/opt/nexus:/usr/sbin/nologin\n"
        "vault_svc:x:1003:1003:Vault Service:/opt/vault:/usr/sbin/nologin\n"
    ),
    "/etc/shadow": "Permission denied: insufficient privileges\n",
    "/etc/nexus/ldap.conf": (
        "# NEXUS Corp LDAP Configuration\n"
        "URI ldap://nexus-ldap-srv:389\n"
        "BASE dc=nexuscorp,dc=local\n"
        "BINDDN cn=admin,dc=nexuscorp,dc=local\n"
        "# BINDPW stored in /etc/nexus/backup.key\n"
        "TLS_REQCERT never\n"
        "# WARNING: Anonymous bind is currently enabled\n"
    ),
    "/etc/nexus/network.conf": (
        "# Internal Network Map\n"
        "SUBNET=10.0.1.0/24\n"
        "GATEWAY=10.0.1.1\n"
        "DNS=10.0.1.2\n"
        "LDAP_SRV=10.0.1.20\n"
        "VAULT_SRV=10.0.1.50\n"
    ),
    "/etc/nexus/backup.key": (
        "# Encrypted backup key\n"
        "LDAP_ADMIN_PASS=Ldap@dm1n_2024\n"
        "# Vault master pass stored separately - see CEO memo\n"
    ),
    "/var/log/auth.log": (
        "Mar 15 02:14:33 nexus-internal sshd[4421]: Failed password for devops from 10.0.1.30\n"
        "Mar 15 02:14:35 nexus-internal sshd[4421]: Accepted password for sysop from 10.0.1.10\n"
        "Mar 15 03:00:01 nexus-internal CRON[4510]: pam_unix(cron:session): session opened for user root\n"
        "Mar 16 14:22:10 nexus-internal sshd[5102]: Accepted publickey for vault_svc from 10.0.1.50\n"
    ),
    "/var/log/nexus-app.log": (
        "[2024-03-15 08:00:12] INFO: Vault service started on port 8443\n"
        "[2024-03-15 08:00:13] INFO: LDAP connection established\n"
        "[2024-03-15 09:45:22] WARN: Multiple failed login attempts from 192.168.1.105\n"
        "[2024-03-15 14:22:10] INFO: vault_svc authenticated via LDAP with clearance_level=5\n"
    ),
    "/var/log/cron.log": "Mar 15 03:00:01 CRON: Running /home/sysop/maintenance.sh\n",
    "/tmp/debug_dump.txt": (
        "=== DEBUG DUMP ===\n"
        "LDAP anonymous bind test: SUCCESS\n"
        "Query: ldapsearch -x -H ldap://nexus-ldap-srv -b 'dc=nexuscorp,dc=local' '(clearance_level>=4)'\n"
        "Result: 3 entries found\n"
        "NOTE: vault_svc has clearance_level=5 - can access CEO vault\n"
        f"\nFlag for this level: {FLAGS[4]}\n"
    ),
    "/opt/nexus-tools/scanner.py": (
        "#!/usr/bin/env python3\n"
        "# Internal vulnerability scanner\n"
        "import ldap3\n"
        "server = ldap3.Server('ldap://nexus-ldap-srv', port=389)\n"
        "conn = ldap3.Connection(server)  # anonymous bind\n"
        "conn.bind()\n"
        "conn.search('dc=nexuscorp,dc=local', '(objectClass=*)', attributes=['*'])\n"
        "for entry in conn.entries:\n"
        "    print(entry)\n"
    ),
    "/opt/nexus-tools/cleanup.sh": "#!/bin/bash\n# Placeholder\necho 'Nothing to clean'\n",
}


@app.route("/level/4/ssh", methods=["POST"])
@team_required
def level4_ssh():
    """Simulated SSH terminal."""
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username == "sysop" and password == "master":
        session["ssh_authenticated"] = True
        return jsonify({
            "success": True,
            "message": (
                "Linux nexus-internal-srv 5.15.0 #1 SMP x86_64 GNU/Linux\n"
                f"Last login: {__import__('datetime').datetime.now().strftime('%a %b %d %H:%M:%S %Y')} from 10.0.1.10\n"
                "sysop@nexus-internal-srv:~$ "
            )
        })
    return jsonify({"success": False, "message": "Permission denied (publickey,password)."}), 401


@app.route("/level/4/cmd", methods=["POST"])
@team_required
def level4_cmd():
    """Process simulated SSH commands."""
    if not session.get("ssh_authenticated"):
        return jsonify({"error": "Not authenticated"}), 401

    cmd = request.form.get("command", "").strip()
    if not cmd:
        return jsonify({"output": ""})

    parts = cmd.split()
    command = parts[0] if parts else ""

    output = ""

    if command == "ls":
        target = parts[-1] if len(parts) > 1 else "/home/sysop/"
        # Normalize path
        if not target.startswith("/"):
            target = "/home/sysop/" + target
        if not target.endswith("/"):
            target += "/"
        entries = SSH_FILESYSTEM.get(target)
        if entries:
            output = "  ".join(entries)
        else:
            output = f"ls: cannot access '{target}': No such file or directory"

    elif command == "cat":
        if len(parts) < 2:
            output = "cat: missing operand"
        else:
            filepath = parts[1]
            if not filepath.startswith("/"):
                filepath = "/home/sysop/" + filepath
            content = SSH_FILES.get(filepath)
            if content:
                output = content
            else:
                output = f"cat: {filepath}: No such file or directory"

    elif command == "pwd":
        output = "/home/sysop"

    elif command == "whoami":
        output = "sysop"

    elif command == "id":
        output = "uid=1001(sysop) gid=1001(sysop) groups=1001(sysop),27(sudo),1010(nexus-ops)"

    elif command == "uname":
        output = "Linux nexus-internal-srv 5.15.0-91-generic #101-Ubuntu SMP x86_64 GNU/Linux"

    elif command in ("find", "locate"):
        if "ldap" in cmd.lower():
            output = "/etc/nexus/ldap.conf\n/opt/nexus-tools/scanner.py"
        elif "key" in cmd.lower() or "pass" in cmd.lower():
            output = "/etc/nexus/backup.key\n/home/sysop/.ssh/id_rsa"
        elif "vault" in cmd.lower():
            output = "/var/log/nexus-app.log\n/opt/nexus-tools/scanner.py"
        else:
            output = "find: specify search criteria"

    elif command == "grep":
        search_term = parts[1] if len(parts) > 1 else ""
        if "vault" in search_term.lower() or "clearance" in search_term.lower():
            output = (
                "/var/log/nexus-app.log: vault_svc authenticated via LDAP with clearance_level=5\n"
                "/tmp/debug_dump.txt: vault_svc has clearance_level=5 - can access CEO vault\n"
                "/home/sysop/notes.txt: CEO vault requires clearance_level >= 5"
            )
        elif "ldap" in search_term.lower():
            output = (
                "/etc/nexus/ldap.conf: URI ldap://nexus-ldap-srv:389\n"
                "/home/sysop/notes.txt: LDAP server at ldap://nexus-ldap-srv:389"
            )
        elif "password" in search_term.lower() or "pass" in search_term.lower():
            output = "/etc/nexus/backup.key: LDAP_ADMIN_PASS=Ldap@dm1n_2024"
        else:
            output = f"grep: nothing found for '{search_term}'"

    elif command == "help":
        output = "Available commands: ls, cat, pwd, whoami, id, uname, find, grep, help, clear, exit"

    elif command == "clear":
        output = "__CLEAR__"

    elif command == "exit":
        session.pop("ssh_authenticated", None)
        output = "__DISCONNECT__"

    else:
        output = f"-bash: {command}: command not found"

    return jsonify({"output": output, "prompt": "sysop@nexus-internal-srv:~$ "})


# ---------------------------------------------------------------------------
# LEVEL 5 – LDAP Enumeration
# ---------------------------------------------------------------------------

@app.route("/level/5")
@team_required
def level5():
    return render_template("levels/level5.html",
                           solved=5 in get_team_progress(session["team_id"]))


@app.route("/level/5/ldap-search", methods=["POST"])
@team_required
def level5_ldap():
    """
    Simulated LDAP search interface.
    Players need to enumerate the directory to find vault_svc credentials.
    """
    base_dn = request.form.get("base_dn", "dc=nexuscorp,dc=local")
    search_filter = request.form.get("filter", "(objectClass=*)")
    attributes = request.form.get("attributes", "*")
    bind_dn = request.form.get("bind_dn", "")
    bind_pass = request.form.get("bind_pass", "")

    db = get_vuln_db()

    # Check authentication
    authenticated = False
    if not bind_dn and not bind_pass:
        # Anonymous bind – allowed per config
        authenticated = True
        auth_method = "anonymous"
    elif bind_dn == "cn=admin,dc=nexuscorp,dc=local" and bind_pass == "Ldap@dm1n_2024":
        authenticated = True
        auth_method = "admin"
    else:
        return jsonify({
            "success": False,
            "message": "ldap_bind: Invalid credentials (49)"
        }), 401

    if not authenticated:
        return jsonify({"success": False, "message": "Bind failed"}), 401

    # Parse filter (simplified)
    results = []
    try:
        rows = db.execute("SELECT * FROM ldap_directory").fetchall()
        for row in rows:
            entry = dict(row)
            # Simple filter matching
            include = False
            if search_filter == "(objectClass=*)" or "objectClass=*" in search_filter:
                include = True
            elif "clearance_level>=4" in search_filter or "clearance_level>=5" in search_filter:
                if entry.get("clearance_level", 0) >= 4:
                    include = True
            elif "uid=" in search_filter:
                uid_match = search_filter.split("uid=")[1].rstrip(")")
                if entry.get("uid") == uid_match:
                    include = True
            elif "cn=" in search_filter:
                cn_match = search_filter.split("cn=")[1].rstrip(")")
                if cn_match.lower() in entry.get("cn", "").lower():
                    include = True
            elif "ou=" in search_filter:
                ou_match = search_filter.split("ou=")[1].rstrip(")")
                if entry.get("ou") == ou_match:
                    include = True

            if include:
                # Filter attributes if specified
                if attributes != "*":
                    attr_list = [a.strip() for a in attributes.split(",")]
                    entry = {k: v for k, v in entry.items() if k in attr_list or k == "dn"}
                # Redact password hash for anonymous unless specifically requested
                if auth_method == "anonymous" and "userPassword" in entry and attributes == "*":
                    entry["userPassword"] = "[REDACTED - bind required]"
                results.append(entry)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({
        "success": True,
        "bind": auth_method,
        "num_results": len(results),
        "results": results,
        "flag": FLAGS[5] if len(results) > 0 and auth_method == "admin" else None,
        "hint": "Crack vault_svc's hash. The CEO Vault runs a hidden API — you'll need to fuzz it." if auth_method == "admin" else None
    })


# ---------------------------------------------------------------------------
# LEVEL 6 – Vault API Fuzzing (ffuf)
# ---------------------------------------------------------------------------

VAULT_API_TOKEN = "dragon"

VAULT_API_WORDLIST = [
    "status", "health", "config", "logs", "backup", "archives",
    "users", "admin", "auth", "login", "register", "docs", "files",
    "search", "upload", "download", "api", "v1", "v2", "internal",
    "external", "public", "private", "secret", "keys", "tokens",
    "sessions", "audit", "reports", "dashboard", "metrics", "analytics",
    "alerts", "notifications", "settings", "preferences", "profiles",
    "accounts", "permissions", "roles", "groups", "teams", "projects",
    "tasks", "resources", "assets", "images", "media", "storage",
    "cache", "queue", "jobs", "workers", "nodes", "clusters",
    "databases", "tables", "schemas", "migrations", "backups", "restore",
    "sync", "export", "import", "debug", "test", "ping", "info",
    "version", "help", "readme", "changelog", "license", "about",
    "contact", "support", "feedback", "monitor", "trace", "deploy",
    "build", "release", "certs", "secrets", "env", "variables",
]

VAULT_API_RESPONSES = {
    "status": (200, {
        "service": "nexus-vault",
        "version": "3.2.1",
        "status": "operational",
        "node": "vault-01",
    }),
    "health": (200, {
        "status": "healthy",
        "uptime_hours": 847,
        "memory_pct": "42%",
    }),
    "config": (403, {
        "error": "Insufficient privileges",
        "required_role": "root",
        "your_role": "service_account",
    }),
    "logs": (200, {
        "recent_entries": [
            {"ts": "2024-03-15T14:22:10Z", "action": "auth_success", "user": "vault_svc"},
            {"ts": "2024-03-15T09:45:22Z", "action": "access_denied", "user": "anonymous"},
            {"ts": "2024-03-14T23:11:05Z", "action": "doc_retrieved", "doc_id": 73, "user": "vault_svc"},
            {"ts": "2024-03-14T18:30:00Z", "action": "backup_completed", "docs_archived": 95},
        ],
    }),
    "backup": (200, {
        "service": "vault-backup",
        "last_run": "2024-03-15T03:00:00Z",
        "status": "completed",
        "next_run": "2024-03-22T03:00:00Z",
    }),
}

VAULT_TARGET_DOC_ID = "73"


@app.route("/level/6")
@team_required
def level6():
    return render_template("levels/level6.html",
                           solved=6 in get_team_progress(session["team_id"]))


@app.route("/level/6/api-wordlist.txt")
def level6_wordlist():
    """Downloadable wordlist for Phase 1 directory fuzzing."""
    content = "\n".join(VAULT_API_WORDLIST) + "\n"
    return content, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/level/6/vault-api/archives")
def level6_archives():
    """
    Archives endpoint — Phase 2 target.
    Without doc_id: returns metadata hinting at document range.
    With doc_id=73: returns classified documents + flag.
    Other doc_ids: returns 'not found' (uniform response for ffuf filtering).
    """
    token = request.headers.get("X-Vault-Token", "")
    if token != VAULT_API_TOKEN:
        return jsonify({
            "error": "Authentication required",
            "hint": "X-Vault-Token header missing or invalid",
        }), 401

    doc_id = request.args.get("doc_id")

    if doc_id is None:
        return jsonify({
            "service": "vault-archives",
            "status": "active",
            "message": "Specify doc_id parameter to retrieve documents.",
            "total_classified": 95,
        })

    if str(doc_id) == VAULT_TARGET_DOC_ID:
        db = get_vuln_db()
        docs = db.execute(
            "SELECT document_name, classification, content FROM ceo_vault"
        ).fetchall()
        return jsonify({
            "access": "GRANTED",
            "clearance": "TOP SECRET",
            "vault_svc_verified": True,
            "documents": [dict(d) for d in docs],
            "message": "CEO Vault breach complete. All classified documents retrieved.",
        })

    return jsonify({
        "error": "Document not found",
        "doc_id": doc_id,
        "status": "restricted",
    })


@app.route("/level/6/vault-api/<path:endpoint>")
def level6_api(endpoint):
    """
    Fuzzable vault API catch-all.
    Only endpoints in VAULT_API_RESPONSES are valid; everything else → 404.
    Requires X-Vault-Token header (cracked vault_svc password from Level 5).
    """
    endpoint = endpoint.strip("/")

    token = request.headers.get("X-Vault-Token", "")
    if token != VAULT_API_TOKEN:
        return jsonify({
            "error": "Authentication required",
            "hint": "X-Vault-Token header missing or invalid",
        }), 401

    if endpoint in VAULT_API_RESPONSES:
        code, body = VAULT_API_RESPONSES[endpoint]
        return jsonify(body), code

    return jsonify({"error": "Endpoint not found", "code": 404}), 404


# ---------------------------------------------------------------------------
# API – Hints
# ---------------------------------------------------------------------------

HINTS = {
    1: [
        "The employee portal has very common credentials. Think: what would a lazy sysadmin use?",
        "Use Hydra with a SHORT custom wordlist — long wordlists hit connection limits. Create one with the 10 most common passwords.",
        "hydra -l admin -P wordlist.txt TARGET https-post-form '/level/1/login:username=^USER^&password=^PASS^:S=Administrator' -V -t 1 -f",
    ],
    2: [
        "The search field doesn't sanitize input. Classic SQL injection territory.",
        "Try entering: ' OR 1=1 -- in the search box to see what happens.",
        "There are more tables than what's visible. Use a tool to enumerate the full schema.",
        "sqlmap -u 'TARGET/level/2/search?search=test' --dbms=sqlite --delay=2 --tables --batch",
    ],
    3: [
        "Look at the length of each hash — it tells you which algorithm was used.",
        "Use a password cracking tool with a large wordlist. Focus on the sysop account.",
        "hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt  (mode 0 = MD5)",
    ],
    4: [
        "Start by listing the home directory. Look for readable files.",
        "Check hidden files and history files — admins leave traces.",
        "Explore system config directories. The flag is inside one of the files.",
        "cat /tmp/debug_dump.txt",
    ],
    5: [
        "LDAP often allows unauthenticated access. Try leaving the credentials blank.",
        "Enumerate all directory entries with a broad search filter, then look for service accounts.",
        "You found admin credentials in Level 4. Binding as admin exposes more attributes.",
        "The account you need has vault clearance — look for attributes that hint at access level or tokens.",
    ],
    6: [
        "The API uses token-based authentication. Check the log fragment — it tells you the header name.",
        "Use ffuf with the wordlist to fuzz endpoint names. Filter out 404 responses to find what exists.",
        "One endpoint lists available documents and tells you how many there are — fuzz its parameters next.",
        "Another endpoint records recent API activity. It may reveal which document was recently accessed.",
        "Use -fw to filter responses by word count so only the interesting ones stand out.",
    ],
}

@app.route("/hint/<int:level>/<int:hint_num>")
@team_required
def get_hint(level, hint_num):
    hints = HINTS.get(level, [])
    if 0 <= hint_num < len(hints):
        return jsonify({"hint": hints[hint_num], "total": len(hints)})
    return jsonify({"error": "No more hints available"}), 404


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "operational", "service": "NEXUS Corp CTF Platform"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_databases()
    app.run(host="0.0.0.0", port=5000, debug=True)
