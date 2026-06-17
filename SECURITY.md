# Security Notes

## Secrets handling

- **Never commit** `auth.json` or `.env` — both are gitignored. Use `.env.example`
  as the template.
- SmartUp API credentials are read from `SMARTUP_USERNAME` / `SMARTUP_PASSWORD`
  env vars, falling back to `auth.json` (gitignored).
- The target database password is read from `DB_PASSWORD` (or a full `DB_URL`).
  There is **no** hardcoded password in source anymore.

## ⚠️ Action required: rotate the exposed Fernet key

The repository previously contained a real Airflow `FERNET_KEY` in `.env`.
Even though `.env` is now gitignored, that key must be treated as compromised:

1. Generate a new key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Put it in your local `.env` as `FERNET_KEY=...`.
3. If you have stored Airflow Connections/Variables encrypted with the old key,
   re-create them (rotating the key invalidates existing encrypted values).
4. Purge the old key from git history if it was ever committed
   (e.g. `git filter-repo`), and change the default `airflow`/`airflow`
   web credentials.

## Other hardening applied

- API error responses are no longer dumped verbatim to logs (they may contain
  PII/tokens); only status code and a truncated, sanitized snippet are logged.
- `requests` uses a session with retry/backoff instead of `sys.exit` on failure.
