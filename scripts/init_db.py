#!/usr/bin/env python3
"""
NEXUS Corp CTF — Database initialization script
Run this separately if you need to reset/rebuild the databases.

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --reset    # Drop and recreate everything
"""

import sys
import os
import argparse

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import init_databases, DB_DIR, MAIN_DB, VULN_DB


def reset_databases():
    """Remove existing databases and recreate them."""
    for db_path in (MAIN_DB, VULN_DB):
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"  Removed: {db_path}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Initialize NEXUS Corp CTF databases")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all databases")
    args = parser.parse_args()

    print("=" * 50)
    print("  NEXUS Corp CTF — Database Setup")
    print("=" * 50)
    print()

    if args.reset:
        print("[!] Resetting databases...")
        reset_databases()

    print("[*] Initializing databases...")
    init_databases()

    print(f"[+] Main DB:       {MAIN_DB}")
    print(f"[+] Vulnerable DB: {VULN_DB}")
    print()
    print("[✔] Databases ready.")
    print()
    print("Database contents:")
    print("  nexus_main.db:")
    print("    - teams           (CTF team registration)")
    print("    - progress        (Level completion tracking)")
    print("    - attack_log      (Request logging)")
    print()
    print("  nexus_vulnerable.db:")
    print("    - portal_users    (Level 1 — weak credentials)")
    print("    - hr_employees    (Level 2 — SQL injection target)")
    print("    - ssh_credentials (Level 2/3 — hidden table with hashes)")
    print("    - ldap_directory  (Level 5 — LDAP enumeration)")
    print("    - ceo_vault       (Level 6 — vault API fuzzing target)")


if __name__ == "__main__":
    main()
