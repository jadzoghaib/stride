# Deploying the Stride demo

A public, shareable link to the working product, on a free instance.

**Registration is open**, so visitors can make their own account rather than
share seeded credentials. That is a choice with two costs, and neither is
hypothetical:

- **Nothing in this system sends email.** `email_outbox` records what a person
  is owed and the schema comment says `sent_at` stays NULL *"forever until a
  provider is attached"*. Someone who registers **can sign in and use
  everything** — `email_verified` gates no route, it is only a badge in
  Settings — but can never confirm their address and **can never reset a
  forgotten password**. The only recovery is a second account.
- **The terms and privacy policy are drafts.** Every legal page renders a status
  line saying so, and the privacy policy still states that the registered entity
  and representative *"will replace this paragraph before public launch"*. Real
  personal data now arrives under those terms.

The product does honour all six GDPR rights, including one-click export and an
erasure that anonymises the person, so anyone who registers can get their data
back or have it removed. What is missing is the controller identity in front of
them, which is a paragraph rather than a project.

> [!important] To close it again
> Set `STRIDE_ALLOW_SIGNUP` to `0` in [`render.yaml`](../render.yaml) and let it
> redeploy. Registration then returns 403, the sign-in page stops offering the
> form, and the deployment collects nothing. That is the right setting for a
> link sent to people you do not know.

§8.5 of the business plan lists what goes to counsel before this is a real front
door rather than a demo that happens to accept accounts.

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
curl -s $URL/api/meta                     # signup_open + demo_accounts
```

`signup_open` tells you which deployment you have. **`true` means real people
can create accounts on it** — check that is what you intended before sharing the
link widely, because it is the difference between a demo that collects nothing
and one holding strangers' email addresses under draft terms.

To confirm a *closed* deployment really is closed:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
     -X POST $URL/api/auth/register \
     -H 'Content-Type: application/json' -d '{}'
                                          # 403 when closed
```

The empty body is deliberate: the gate runs ahead of request validation, so a
malformed request is answered with the policy rather than a complaint about a
missing field.

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
| `STRIDE_ALLOW_SIGNUP` | `1` | Open. `0` closes it and collects nothing |
| `STRIDE_DEMO_ACCOUNTS` | `1` | Whether the sign-in page lists the seeded accounts. Read by the client from `/api/meta`; independent of the row above |
| `STRIDE_EMAIL_DELIVERY` | **unset (`0`)** | Whether anything delivers the mail this system queues. Off in fact — turn it on in the same change that attaches a provider |
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
  and send nothing. **With signup open this is visible to real users**, so the
  interface no longer pretends otherwise: `STRIDE_EMAIL_DELIVERY` is off and the
  sign-in page says "No password recovery on this deployment" in place of the
  link. The mechanism still works underneath — a reset token is issued and
  recorded — so an admin reading `/api/admin/outbox` can recover somebody by
  hand. Attaching a provider is what makes it self-service.

  Registration itself never made a promise to break: a local account is signed
  in immediately and told nothing about an inbox. The "check your inbox" notice
  belongs to Supabase-backed deployments, where Supabase sends that mail itself.
- **Everyone shares one rate-limit bucket.** `STRIDE_FORWARDED_ALLOW_IPS` is
  unset on purpose, so nobody can pick their own bucket by spoofing a header —
  but that means the limiter sees Render's edge address for every visitor.
  Registration has its own bucket so it cannot starve sign-in, and sign-in
  cannot starve registration; within each, visitors share. Per-visitor limits
  need a proxy configuration that can be trusted, which is a real-users problem
  rather than a demo one.
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
