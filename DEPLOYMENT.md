# Hosted deployment

Deploy the React server and Django API behind one HTTPS origin where possible. Route `/api/`, `/admin/`, and Django `/static/` to the backend, and other routes to the frontend. Serve collected Django static files with the reverse proxy. This avoids cross-site session-cookie restrictions.

## Configuration

Set frontend `VITE_API_BASE_URL=https://your-host.example` **at build time**. Run `npm ci --legacy-peer-deps`, `npm run typecheck`, `npm run build`, then `node .output/server/index.mjs` (configure `PORT` for your platform).

Backend environment:

```dotenv
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<random-secret-at-least-50-characters>
DJANGO_ALLOWED_HOSTS=your-host.example
CORS_ALLOWED_ORIGINS=https://your-host.example
CSRF_TRUSTED_ORIGINS=https://your-host.example
DJANGO_TRUST_PROXY=1
```

Enable proxy trust only when the HTTPS proxy strips client-provided forwarding headers and sets `X-Forwarded-Proto` itself. The API redirects HTTP to HTTPS in production. For separate frontend/API origins, explicitly configure both origins and confirm browser cookie policies; one origin is preferred.

Install backend requirements, fetch Git LFS weights, then:

```sh
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py check --deploy
gunicorn brain_backend.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 1 --timeout 600
```

Use the header's Sign in link to authenticate a staff account, then return to the workspace. POST requests obtain a CSRF token and include the authenticated session. Provision individual staff accounts through Django administration. Anonymous and non-staff users cannot analyze scans or send email in production.

## Runtime requirements

MRI registration is CPU- and memory-intensive and synchronous. Set the reverse proxy request timeout to match the worker timeout and limit uploads to 128 MB at the proxy. Measure memory with representative scans before scaling; each worker loads its own models. A durable job queue is still needed for high-volume processing.

SQLite is the current database. Keep its file on persistent storage and back it up; do not run multiple replicas against independent database files. A managed relational database and a defined retention policy are required before multi-user clinical use. The saved-report UI currently uses browser local storage, not an access-controlled server report archive.

SMTP is optional. Set `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL` as deployment secrets. Console email cannot claim successful delivery.

## Release checks

- Fetch and validate the cerebellum bundle; missing/incompatible artifacts must return 503.
- Run TypeScript, production build, cerebellum contract tests and production access tests.
- Confirm anonymous API calls fail, staff sessions work, and CSRF checks reject missing tokens.
- Check HTTPS, model availability, uploads and reports on the actual host.
- Keep patient data, logs, credentials and local databases out of Git.

This release improves deployment hygiene and the research workflow. It does not establish diagnostic accuracy, regulatory approval, or clinical deployment readiness.

Reference: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

## Dependency audit (2026-11-10)

`npm audit --omit=dev` reports zero known vulnerabilities after patching TanStack Start, Zod and the runtime dependency tree. The full development audit still reports seven moderate advisories in the TypeScript ESLint / minimatch toolchain. These tools do not ship in the built server; continue tracking the upstream fix.
