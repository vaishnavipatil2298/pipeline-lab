# pipeline-lab

A small FastAPI todos API built as a hands-on lab for the whole delivery
pipeline: tests → Docker → CI → managed Postgres → Terraform → Kubernetes →
observability.

- **Live:** https://pipeline-lab.onrender.com
- **Repo:** https://github.com/vaishnavipatil2298/pipeline-lab

## Endpoints

| Method | Path          | Description                          |
| ------ | ------------- | ------------------------------------ |
| GET    | `/health`     | liveness check                       |
| GET    | `/todos`      | list todos                           |
| GET    | `/todos/{id}` | get one todo (404 if missing)        |
| POST   | `/todos`      | create a todo (201)                  |
| PUT    | `/todos/{id}` | partial update (404 if missing)      |
| DELETE | `/todos/{id}` | delete (204, 404 if missing)         |
| GET    | `/metrics`    | Prometheus metrics                   |

Interactive docs at `/docs`.

## Architecture

```
app/main.py       API layer only — contains no SQL
      │
      ▼
app/database.py   all storage access; the same five functions for every backend
      │
      ├── DATABASE_URL set  →  Postgres (psycopg 3)
      └── otherwise         →  SQLite file (DB_PATH)
```

The backend is chosen at call time from the environment, so `main.py` never
changes when storage does. Postgres runs in production and containers; SQLite
keeps local runs and the fast test job dependency-free.

### Why Postgres

SQLite lives in a file on the web service's disk. Render's free tier has an
ephemeral filesystem, so that file (and every todo in it) disappeared on each
restart or redeploy. Data now lives in a managed Postgres instance, which
survives restarts.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate            # or: source .venv/bin/activate
pip install -r requirements.txt

# SQLite (zero setup):
uvicorn app.main:app --reload

# or point at Postgres:
docker run -d --name pl-pg -p 5432:5432 \
  -e POSTGRES_USER=pipeline_lab -e POSTGRES_PASSWORD=pipeline_lab \
  -e POSTGRES_DB=pipeline_lab postgres:16-alpine
# then: set DATABASE_URL=postgresql://pipeline_lab:pipeline_lab@localhost:5432/pipeline_lab
```

Visit http://localhost:8000/docs. Copy `.env.example` for the full set of
environment variables.

## Tests

```bash
pytest -v                       # SQLite by default
```

The same suite runs against Postgres when `TEST_DATABASE_URL` is set:

```bash
export TEST_DATABASE_URL=postgresql://pipeline_lab:pipeline_lab@localhost:5432/pipeline_lab
pytest -v
```

Every test resets the table first, so auto-assigned ids line up on both
backends.

## Docker

```bash
docker build -t pipeline-lab .
docker run -p 8000:8000 -e DATABASE_URL="postgresql://user:pass@host:5432/db" pipeline-lab
```

## Full local stack (app + Postgres + Prometheus + Grafana)

```bash
docker compose up --build
```

| Service    | URL                              |
| ---------- | -------------------------------- |
| app        | http://localhost:8000            |
| Prometheus | http://localhost:9090            |
| Grafana    | http://localhost:3000 (admin/admin) |

Grafana is provisioned with the Prometheus datasource and a `pipeline-lab`
dashboard: total requests, request rate, 5xx rate, per-handler/status
breakdown, and p50/p95 latency. If a host port is already taken it can be
remapped, e.g.:

```bash
APP_PORT=18000 PROMETHEUS_PORT=19090 GRAFANA_PORT=13000 docker compose up
```

## Kubernetes (minikube)

```powershell
pwsh -File .\scripts\deploy-minikube.ps1
kubectl -n pipeline-lab port-forward svc/pipeline-lab 8080:80
curl http://127.0.0.1:8080/health
```

`k8s/` holds the manifests (kustomize): the app plus an in-cluster Postgres
backed by a PersistentVolumeClaim, so data survives pod restarts.
`kubectl apply -k k8s` applies them directly.

## Terraform (Render)

`infra/terraform/` provisions the managed Postgres instance — and, optionally,
the web service — as code.

```powershell
$env:RENDER_API_KEY  = "rnd_..."
$env:RENDER_OWNER_ID = "tea-..."
cd infra/terraform
terraform init
terraform plan
terraform apply
```

Only the database is managed by default (`manage_web_service = false`), so an
existing live service is left untouched. To bring the current service under
Terraform instead of creating a second one, set `manage_web_service = true`
in your tfvars and import it:

```bash
terraform import 'render_web_service.app[0]' <srv-xxxxx>
```

`terraform output -raw postgres_internal_connection_string` returns the
`DATABASE_URL` to set on the service (Terraform wires it automatically when it
manages the service). Keep `region` aligned with the web service so the
internal URL is reachable.

## Smoke test

`scripts/smoke-test.ps1` drives a running instance end to end — create, read,
update, delete, the 404 paths, and `/metrics`. It targets the live deployment
by default and works against an empty database.

```powershell
pwsh -File .\scripts\smoke-test.ps1                      # live Render
pwsh -File .\scripts\smoke-test.ps1 -Local               # launch a local SQLite server
pwsh -File .\scripts\smoke-test.ps1 -BaseUrl "http://localhost:8000"
```

## CI

`.github/workflows/ci.yml` runs on every push and PR:

1. **Tests (SQLite)** — the default suite.
2. **Tests (Postgres)** — the same suite against a Postgres service container.
3. **Build and smoke test container** — builds the image and checks `/health`.

## Project layout

```
app/                 FastAPI app + database layer
tests/               pytest suite (SQLite + Postgres)
scripts/             smoke test, minikube deploy
k8s/                 Kubernetes manifests (kustomize)
infra/terraform/     Render Postgres + web service as code
observability/       Prometheus config + provisioned Grafana dashboard
Dockerfile           container image
docker-compose.yml   app + Postgres + Prometheus + Grafana
```

## Deployment flow (Render)

1. `terraform apply` creates the Postgres instance.
2. Set its internal connection string as `DATABASE_URL` on the web service
   (automatic when `manage_web_service = true`).
3. Render redeploys and `init_db()` creates the table on first boot.
4. Restart the service to confirm todos persist.

Persistence across process restarts has been verified against a real Postgres
both locally and in minikube.
