# Deploying the Stride demo

A public, shareable link to the working product, running on managed
infrastructure, **collecting no personal data from anyone who opens it**.

That last clause is the design of this deployment rather than a side effect.
Registration is closed, so the only way in is the five seeded demo accounts, and
the deployment never holds a real person's email, password or IP beyond a
request log. Two facts make that the right call:

- **Nothing in this system sends email.** `email_outbox` records what a person
  is owed and the schema comment says `sent_at` stays NULL *"forever until a
  provider is attached"*. A stranger who registered could never verify their
  address or reset their password.
- **The terms and privacy policy are drafts.** Every legal page renders a
  status line saying so, and the privacy policy itself states that the
  registered entity and representative *"will replace this paragraph before
  public launch"*.

Closing signup means neither of those has to be solved before you can send a
link. Both must be solved before real users, which is a different project —
see §8.5 of the business plan for what goes to counsel first.

---

## What is deployed

| Service | Image | Notes |
|---|---|---|
| `stride-api` | `infra/docker/Dockerfile.api` | FastAPI on uvicorn, seeds itself on first boot |
| `stride-web` | `infra/docker/Dockerfile.web` | Vite build on nginx, proxies `/api` to the API |
| `stride-db` | Render Postgres | Schema and demo data created on the API's first start |

The browser only ever talks to `stride-web`. The API is reached through the
nginx proxy on the same origin, which is why session cookies work without any
CORS relaxation.

---

## First deploy

Steps 1, 2 and 5 need your Render account — **they cannot be scripted from
here, and nobody should be entering your billing details but you.**

### 1 · Connect the repository

In the Render dashboard: **New → Blueprint**, point it at
`github.com/jadzoghaib/stride`, and let it read [`render.yaml`](../render.yaml)
from the repository root. It will propose two services and one database.

### 2 · Approve the plans

`render.yaml` asks for `starter` instances and a `basic-256mb` database.
**Do not take the free instance type for a link you intend to send** — free
services sleep after inactivity and cold-start for roughly a minute, so the
first person to open your link waits at a blank page. Check the current prices
on Render's pricing page; they are per service per month.

Region is `frankfurt`. The plan is a Spanish company and the demo data
describes EU athletes, so EU residency is the sensible default even for
simulated data.

### 3 · Let it build, then read the API's internal address

Render assigns each service an internal hostname on first deploy. The web
service needs it, and it is the one value `render.yaml` deliberately leaves
blank rather than guessing:

```
STRIDE_API_UPSTREAM = http://<the API's internal address>:<port>
```

Find it on the `stride-api` service page, set it on **`stride-web` → Environment**,
and redeploy the web service.

> **If `stride-web` crash-loops on the very first deploy, this is why.**
> nginx resolves its upstream at start-up and refuses to start if the name does
> not resolve, so a web container that boots before the API exists dies rather
> than waiting. Set the variable, redeploy, and it settles.

### 4 · Confirm it came up

```bash
curl -s https://<your-web-url>/readyz                 # {"status":"ok"}
curl -s https://<your-web-url>/api/meta               # signup_open:false
curl -s -o /dev/null -w '%{http_code}\n' \
     -X POST https://<your-web-url>/api/auth/register \
     -H 'Content-Type: application/json' \
     -d '{"email":"a@b.com","password":"aaaaaaaa","display_name":"x","role":"fan"}'
                                                      # 403
```

The third one is the check that matters. **If it returns 201, the deployment is
open and you should not share the link** until `STRIDE_ALLOW_SIGNUP=0` is set on
`stride-api`.

Then open the link and sign in as `sponsor@demo.stride` / `stride123`. The
sign-in page lists all five accounts; it renders them only when signup is
closed, because that is the only time they are the intended way in.

### 5 · A custom domain, if you want one

Optional. Render issues `https://stride-web-*.onrender.com` with TLS, which is
a perfectly good link to send. If you add a domain, update `STRIDE_CORS_ORIGINS`
and `STRIDE_PUBLIC_URL` on the API to match.

---

## Environment

Set by `render.yaml`; listed here because a second environment will need them.

| Variable | Value | Why |
|---|---|---|
| `STRIDE_ENV` | `production` | Turns on secure cookies; the app refuses to boot on the dev secret |
| `STRIDE_SECRET` | generated | Signs sessions. Never commit one |
| `STRIDE_DATABASE_URL` | from the database | Absent, the API falls back to SQLite on the disk |
| `STRIDE_ALLOW_SIGNUP` | `0` | **The line that makes the link safe to share** |
| `STRIDE_CORS_ORIGINS` | the web URL | Same-origin in practice, since nginx proxies |
| `STRIDE_PUBLIC_URL` | the web URL | Used to build links inside emails that are recorded but not sent |
| `STRIDE_FORWARDED_ALLOW_IPS` | `*` | Render terminates TLS at its edge; without this the rate limiter keys on the proxy |
| `STRIDE_MEDIA_DIR` | `/data/media` | On the mounted disk, so uploads survive a restart |
| `STRIDE_CHAOS` | `0` | The fault-injection middleware stays off outside dev |
| `STRIDE_API_UPSTREAM` | *(web service)* | Set by hand once — see step 3 |

---

## Known limits of this deployment

Honest list, so nothing here is a surprise when someone asks.

- **No email.** Verification, password reset and change-of-address all record a
  row and send nothing. Invisible while signup is closed.
- **Media on a disk, not object storage.** Fine for a one-instance demo. It
  does not survive scaling past one instance, and it is the first thing to
  change before real uploads matter.
- **Platform connectors are simulated.** Instagram, TikTok and YouTube data is
  generated, and every surface that shows audience figures says so on the page.
- **One instance.** No horizontal scaling, so no session or upload affinity
  problems — and no redundancy either.
- **Demo data resets only if you delete the database.** The seed is idempotent
  and will not overwrite a database that already has rows.

---

## Three faults this deployment work uncovered

None of these were visible while the product only ever ran from a checkout,
and all three would have failed the first real deploy:

1. **The API image could not start.** `ENV PATH` pointed at
   `/app/apps/api/.venv/bin`, but `uv sync --directory apps/api` resolves the
   workspace root and creates the environment at `/app/.venv`. `stride` was
   never on `PATH`.
2. **`httpx` was declared as a dev dependency** and imported at module scope by
   `proofcheck.py`, which `admission → seed → cli` pulls in on the way to
   serving. Present wherever tests ran, absent from `uv sync --no-dev`.
3. **`/data` was root-owned** while the container runs as `stride`, so the
   process could not open its own database.

`docker compose -f infra/docker-compose.yml up --build` now runs the same
images the platform will, which is the cheapest way to catch the fourth one.
