# Windows local development

From the complete project directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-all.ps1
```

Open http://127.0.0.1:8080/axes/cerebellar-dysfunction. Ctrl+C stops both processes. Logs are written to `backend-stdout.log` and `backend-stderr.log`.

For initial installation, follow README.md. The launcher expects `backend/.venv` and installed npm dependencies. It explicitly enables development mode for localhost.

The original development machine's virtual environment reuses installed scientific libraries and the sibling `.test-deps` directory. That environment is not portable. Fresh clones should create their own virtual environment and install the requirements.
