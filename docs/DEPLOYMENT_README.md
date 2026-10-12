# Deployment

## Goal

Deploy PlayerWorth with separate frontend, backend, and database services.

## Production Layout

```text
Browser
  |
  v
Vercel / Next.js
  |
  v
Railway / FastAPI
  |
  +----> Supabase PostgreSQL
  |
  +----> saved ML model artifact
```

## Environment Variables

### Frontend

```text
NEXT_PUBLIC_API_BASE_URL=
```

### Backend

```text
DATABASE_URL=
MODEL_PATH=
MODEL_NAME=
MODEL_VERSION=
CORS_ORIGINS=
```

No secrets in Git.

## Supabase

1. create project
2. obtain PostgreSQL connection string
3. run Alembic migrations
4. import real processed data
5. verify indexes
6. configure backups/security appropriately

## Railway

Deploy FastAPI.

Requirements:

- production start command
- environment variables
- model artifact available
- health endpoint
- logs
- database connectivity

Example start style:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Adapt path to actual project structure.

## Vercel

Deploy Next.js.

Configure:

```text
NEXT_PUBLIC_API_BASE_URL=https://<backend>
```

Do not expose private backend/database secrets to client-side environment variables.

## CORS

Production backend should allow only intended frontend origins.

Avoid:

```text
*
```

unless specifically justified for a public API.

## Model Artifact

The deployment must use the exact saved pipeline selected as production.

Options:

1. bundle artifact into backend build
2. download versioned artifact during deployment
3. later use object storage/model registry

For V1, bundling a small artifact is acceptable.

## Health Checks

Backend:

```http
GET /api/v1/health
```

Optionally include:

- database reachable
- model loaded

Do not reveal credentials/internal stack traces.

## Observability

Minimum:

- structured backend logs
- request errors
- startup failures
- model-load failures

Optional later:

- Sentry
- performance monitoring

## Deployment Checklist

- tests passing
- migrations applied
- production model exists
- no fake data
- frontend API URL correct
- CORS correct
- HTTPS
- secrets configured
- health endpoint works
- player search works
- prediction works
- simulator works

## First Codex Prompt

```text
Read README.md and docs/DEPLOYMENT_README.md.

Inspect the existing repository.

Add only the deployment configuration needed for:
- Vercel frontend
- Railway FastAPI backend
- Supabase PostgreSQL
- environment examples
- production start commands

Do not deploy anything automatically.
Do not include real credentials.
Document every manual deployment step.
```
