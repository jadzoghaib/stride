# Deploying the Stride demo

A public, shareable link to the working product, **collecting no personal data
from anyone who opens it**, on a free instance.

That first clause is the design rather than a side effect. Registration is
closed, so the only way in is the seeded demo accounts and the deployment never
holds a real person's email or password. Two facts make that the right call:

- **Nothing in this system sends email.** `email_outbox` records what a person
  is owed and the schema comment says `sent_at` stays NULL *"forever until a
  provider is attached"*. A stranger who registered could never verify their
  address or reset their password.
- **The terms and privacy policy are drafts.** Every legal page renders a
  status line saying so, and the privacy policy itself states that the
  registered entity and representative *"will replace this paragraph before
  public launch"*.

Closing signup means neither has to be solved before you can send a link. Both
must be solved before real users — a different project, and §8.5 of the business
plan lists what goes to counsel first.

---

## One container, on purpose

[`Dockerfile.demo`](../infra/docker/Dockerfile.demo) builds the client and the
API into a single image: uvicorn serves the API and the built SPA from the same
process, with SQLite seeded on first boot.

The two-container build — `Dockerfile.api` behind `Dockerfile.web`'s nginx — is
the right shape for a real deployment and is still there. It is not the right
shape for *this* job. Two containers means two instances, a private network
between them and an upstream address wired by hand; on Render that is two paid
services plus a paid database, which is what makes the Blueprint ask for a card.
One container needs none of it.

It binds `$PORT` and has no attached services, so the same image runs unchanged
on **Render's free tier, Hugging Face Spaces, Koyeb, Fly, or any box with
Docker**. You are not tied to one vendor's billing rules.

```bash
docker build -f infra/docker/Dockerfile.demo -t stride-demo .
docker run -p 8080:8080 -e PORT=8080 -e STRIDE_SECRET=$(openssl rand -hex 32) \
           -e STRIDE_ALLOW_SIGNUP=0 stride-demo
```

---

## Deploying on Render (free)

### 1 · Blueprint

**New → Blueprint**, point it at `github.com/jadzoghaib/stride`, branch `main`.
It reads [`render.yaml`](../render.yaml) from the repository root and proposes
**one** service on the free plan.

> If Render still asks for payment details, the Blueprint is reading an older
> commit. The paid shape — two `starter` services, a private service and a
> `basic-256mb` database — was the first version of this file.

### 2 · Set the two URL variables

Render assigns the URL on first deploy, and it cannot be derived inside the
blueprint: `fromService … property: host` yields a bare hostname, which never
matches the browser's `Origin` header and leaves generated links without a
scheme. So after the first deploy, set both to the service's full URL:

```
STRIDE_CORS_ORIGINS = https://stride-demo-xxxx.onrender.com
STRIDE_PUBLIC_URL   = https://stride-demo-xxxx.onrender.com
```

Then redeploy.

### 3 · Check it before you share it

```bash
URL=https://stride-demo-xxxx.onrender.com

curl -s $URL/readyz                       # {"status":"ready"}
curl -s $URL/api/meta                     # "signup_open":false

curl -s -o /dev/null -w '%{http_code}\n' \
     -X POST $URL/api/auth/register \
     -H 'Content-Type: application/json' -d '{}'
                                          # 403
```

**The third is the one that matters.** If it returns anything but 403 the front
door is open — do not share the link until `STRIDE_ALLOW_SIGNUP=0` is set. An
empty body is deliberate: the gate runs ahead of request validation, so a
malformed request is still answered with the policy rather than a complaint
about a missing field.

Then open the link and sign in as `sponsor@demo.stride` / `stride123`.

---

## The demo accounts

The sign-in page lists five — one per role — and the seed creates **fourteen**,
all with the password `stride123`:

| Listed on the page | Also seeded, same password |
|---|---|
| `athlete@demo.stride` | `athlete2@demo.stride` |
| `club@demo.stride` | `club2@demo.stride`, `club3@demo.stride` |
| `sponsor@demo.stride` | `sponsor2@demo.stride`, `sponsor3@demo.stride` |
| `fan@demo.stride` | `fan2@` … `fan5@demo.stride` |
| `admin@demo.stride` | |

The nine unlisted ones split two ways. `athlete2`, `club2`, `club3`, `sponsor2`
and `sponsor3` exist because the audits need accounts in particular states — an
athlete and a club still sitting in the review queue, second and third sponsor
orgs with their own campaigns. `fan2` through `fan5` are filler, created in a
loop so subscriber counts are not all 1.

**All fourteen are usable on the deployment**, `admin@` included, which reaches
the moderation queue and the admin views. Every one is seeded data with no
personal information in it, which is why this is a note rather than a problem —
but say "fourteen accounts, all public" rather than "five" if anyone asks.

(The count was wrong here twice: five, then ten. `fan{i}@demo.stride` is built
in an f-string, so grepping for the literal address finds one match and misses
four accounts. Counting from the database is the only honest way to do it:
`SELECT email FROM users WHERE email LIKE '%@demo.stride'`.)

---

## Environment

| Variable | Value | Why |
|---|---|---|
| `STRIDE_ENV` | `production` | Secure cookies; the app refuses to boot on the dev secret |
| `STRIDE_SECRET` | generated | Signs sessions. Never commit one |
| `STRIDE_ALLOW_SIGNUP` | `0` | **The line that makes the link safe to share** |
| `STRIDE_DB` | `/home/stride/data/stride.db` | The runtime user's own home — a mounted disk would be root-owned |
| `STRIDE_MEDIA_DIR` | `/home/stride/media` | Same reason |
| `STRIDE_WEB_DIST` | `/app/web` | Set in the image; where the built client lives |
| `STRIDE_CORS_ORIGINS` | the full https:// URL | Set by hand — see step 2 |
| `STRIDE_PUBLIC_URL` | the full https:// URL | Set by hand — see step 2 |
| `PORT` | assigned | The platform picks it; the entrypoint binds it |
| `STRIDE_FORWARDED_ALLOW_IPS` | **unset** | Trusting `*` on a public service would let callers spoof `X-Forwarded-For` and pick their own rate-limit bucket. Unset keys the limiter on the edge address: one shared bucket, stricter than ideal, not spoofable |

---

## Known limits

Honest list, so nothing is a surprise when someone asks.

- **No email.** Verification, password reset and change-of-address record a row
  and send nothing. Invisible while signup is closed.
- **The instance sleeps.** On the free plan it spins down after inactivity and
  cold-starts in roughly a minute. Move to a paid instance before sending the
  link to someone whose time you care about.
- **State resets on restart.** SQLite lives in the container, so a redeploy or a
  wake-from-sleep returns the demo to seed state. For a demonstration that is
  closer to a feature than a fault; for anything else, attach Postgres.
- **Uploads do not survive a restart** for the same reason.
- **Platform connectors are simulated.** Instagram, TikTok and YouTube data is
  generated, and every surface that shows audience figures says so on the page.

---

## Faults this deployment work uncovered

None were visible while the product only ran from a checkout, and every one
would have failed a real deploy:

1. **The API image could not start.** `ENV PATH` pointed at
   `/app/apps/api/.venv/bin`, but `uv sync --directory apps/api` resolves the
   workspace root and creates the environment at `/app/.venv`.
2. **`httpx` was declared dev-only** and imported at module scope by
   `proofcheck.py`, which `admission → seed → cli` pulls in on the way to
   serving. Absent from `uv sync --no-dev`.
3. **`/data` was root-owned** while the container runs as `stride`.
4. **nginx bound port 80** while managed platforms assign `$PORT` and route
   there — the link would have loaded nothing.
5. **nginx capped uploads at 1 MB** against an API documenting 8 MiB.
6. **`sh` stayed PID 1**, so SIGTERM was never forwarded and redeploys dropped
   in-flight requests.
7. **The image health check probed a fixed 8490** regardless of `$PORT`.

Building and running the image is the cheapest way to find the eighth.
