# pipeline-lab

A tiny FastAPI service used as a hands-on lab for Docker, pytest, and GitHub Actions CI/CD.
Part of the [ai-devops-lab](https://github.com/vaishnavipatil2298/ai-devops-lab.git).\30-week learning sprint>

## What's here (Week 1)

- FastAPI app with `/health` and `/todos` endpoints
- pytest tests
- Dockerfile
- GitHub Actions workflow that runs tests + builds the container on every push

## What's coming (Weeks 2–4)

- Real database (SQLite → Postgres)
- Playwright end-to-end tests
- Deployment to Render or Fly.io
- Claude Code + MCP integration for automated code review

## Run locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload

# Run tests
pytest -v
```

Visit `http://localhost:8000/docs` for the interactive API docs.

## Run with Docker

```bash
# Build image
docker build -t pipeline-lab .

# Run container
docker run -p 8000:8000 pipeline-lab

# Check health
curl http://localhost:8000/health
```

## Weekly progress

- **Week 1:** Scaffolding + CI pipeline green
- **Week 2:** Add persistence + more tests
- **Week 3:** Deploy + add Playwright E2E
- **Week 4:** Add observability (logging, metrics)
