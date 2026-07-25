# Synap Support

Backoffice RAG/copiloto (React + Django), independiente del ERP Synap. Integración con Synap solo vía API HTTP.

## Variables de entorno: un solo archivo

**Todo el proyecto Support usa un único `.env` en este directorio** (`support/.env`):

- **Backend (Django)** lo lee desde `config/settings/base.py`.
- **Docker Compose** lo usa con `env_file: ../.env` (relativo al compose en `docker/`).
- **Frontend (Vite)** lo lee con `envDir: ..` en `frontend/vite.config.ts`.

No uses `backend/.env`, `docker/.env` ni `frontend/.env`: crea o edita solo **support/.env**.

### Puesta en marcha

```bash
cd support
cp .env.example .env
# Editar .env: CONFIG_ENCRYPTION_KEY (obligatoria para la UI de configuración), DATABASE_URL, SUPPORT_SYNAP_API_URL, etc.
```

Documentación completa: [docs/PASO_A_PASO_PONER_EN_MARCHA.md](docs/PASO_A_PASO_PONER_EN_MARCHA.md).

- **Backend:** [backend/README.md](backend/README.md)
- **Frontend:** [frontend/README.md](frontend/README.md)
- **Docker:** [docker/README.md](docker/README.md)
- **Docs:** [docs/README.md](docs/README.md)
