# Stride × Supabase — what's wired, what's next

## Wired now: Supabase Auth as the identity provider
`.env` carries your project URL + publishable key. With those set, the API:
- **registers** new accounts against Supabase (`/auth/v1/signup`) — Supabase owns
  credentials, email confirmation, and password reset; Stride stores no password,
  only the role/profile row linked by `auth_id`;
- **verifies logins** via the Supabase password grant, then issues Stride's own
  short-lived session cookie;
- keeps **local PBKDF2 fallback** for the seeded demo accounts (`*@demo.stride`),
  so the demo works regardless of Supabase settings.

Notes:
- If your project has "Confirm email" enabled (Supabase default), new signups get
  a confirmation email and the UI says so; they can sign in after confirming.
  To skip during development: Dashboard → Authentication → Sign In / Up →
  disable "Confirm email".
- Only the publishable (anon) key is used. Never put the service-role key or your
  database password in code or chats — `.env` only, which is gitignored.

## Data on Postgres — wired and switchable
The API now runs on **either** SQLite (default) or Postgres. Set
`STRIDE_DATABASE_URL` in `.env` and everything — schema creation, seeding,
every query — runs on Postgres through the psycopg layer
(`stride_api/pgconn.py` + `stride_api/schema_pg.sql`). No other change.

**Point it at this Supabase project** (put YOUR db password in yourself —
never share it in chats). Use the session pooler DSN from
Dashboard → Connect, which looks like:

```
STRIDE_DATABASE_URL=postgresql://postgres.zgbtjahtqhilbrngvtxw:YOUR_DB_PASSWORD@aws-0-<region>.pooler.supabase.com:5432/postgres
```

Then, from the repo root:

```
uv run stride init     # creates all tables in Supabase + seeds the demo data
uv run stride serve    # same app, now on your Supabase Postgres
```

`uv run stride reset` drops and re-creates the Stride tables (Postgres mode
drops via CASCADE — it only touches the app's own tables).

**Local Postgres for testing** (Docker):

```
docker run -d --name stride-pg -e POSTGRES_PASSWORD=localdev -e POSTGRES_DB=stride -p 55432:5432 postgres:16-alpine
# .env: STRIDE_DATABASE_URL=postgresql://postgres:localdev@127.0.0.1:55432/stride
```

The RLS policies in `infra/supabase/migrations/0001_stride.sql` remain the
defense-in-depth layer for when clients talk to Postgres directly (PostgREST);
the API's service connection enforces the same rules in code today.

## Troubleshooting — the Supabase errors you will actually meet

| Symptom | Cause | Fix |
|---|---|---|
| `could not translate host name "db.zgbtjahtqhilbrngvtxw.supabase.co"` or endless connect timeout | The **direct** connection host is IPv6-only; most home/Windows networks are IPv4 | Use the **pooler** DSN (`...pooler.supabase.com`) from Dashboard → Connect — the one this file recommends |
| `prepared statement "_pg3_0" does not exist` / `...already exists` | Transaction pooler (port 6543) + psycopg's server-side prepared statements | Already fixed in code: `pgconn.py` connects with `prepare_threshold=None`. Prefer the **session** pooler (port 5432) anyway |
| `password authentication failed for user "postgres"` | Wrong password, or special characters in the password not URL-encoded in the DSN | Reset the DB password in Dashboard → Settings → Database; URL-encode symbols (`@` → `%40`, `#` → `%23`, …) |
| `Tenant or user not found` | Pooler DSN needs the project-qualified username | Username must be `postgres.zgbtjahtqhilbrngvtxw`, not plain `postgres` (the dashboard's copy button gets this right) |
| Signup returns 422 `email rate limit exceeded` | Supabase's built-in SMTP allows ~2 confirmation emails/hour | Wait, or wire a custom SMTP provider (Dashboard → Authentication → SMTP) — see docs/costs.md for provider pricing |
| Signup returns 422 `email address ... is invalid` | GoTrue rejects test/undeliverable domains (`example.org` etc.) | Use a real mailbox; for dev, plus-tags work (`you+test1@...`) |
| Auth works locally but fails deployed | `.env` not present in the container/pod | Supply `STRIDE_SUPABASE_URL` / `_ANON_KEY` / `STRIDE_DATABASE_URL` via your deploy's secret store (the Secret block in infra/k8s/stride.yaml) |
