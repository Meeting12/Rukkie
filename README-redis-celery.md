Local Redis + Celery (development)

This project uses Celery for background image analysis. For local development you can run Redis + a worker using Docker Compose.

Start Redis + DB + worker + web (dev):

```bash
# from project root
docker-compose up --build
```

This will:
- Run Postgres (`db`) and pgAdmin (`pgadmin`) as before
- Start Redis on `localhost:6379`
- Start a local Django dev server on `http://localhost:8000`
- Start a Celery worker which uses `CELERY_BROKER_URL=redis://redis:6379/0`

If you prefer to run the worker manually (no Docker):

```bash
# start Redis via Docker only
docker run -p 6379:6379 redis:7

# in a separate terminal (activate your venv)
pip install -r requirements.txt
# set env vars, e.g. on Windows PowerShell:
$env:CELERY_BROKER_URL = 'redis://localhost:6379/0'
$env:CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
python manage.py migrate
celery -A Rukkie worker --loglevel=info
```

Render deployment notes

- `render.yaml` includes a `rukkie-worker` service and a Redis addon. After pushing to Render, configure any secret env vars in the Render dashboard (Stripe keys, database URL, SECRET_KEY, etc.).
- Render's Redis addon provides a managed Redis instance; set `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` to the provided Redis URL in your Render service env vars.
- Ensure you add database migrations to your deploy steps (Render web service `buildCommand` already runs `manage.py migrate` in this repo's `render.yaml`).

Commands to run migrations on Render (via `render` CLI or Dashboard):

```bash
# using render CLI (after login)
render services deploy <service-id>
# or run a one-off shell and run migrations
# (Render dashboard -> New Shell) then:
python manage.py migrate
```
