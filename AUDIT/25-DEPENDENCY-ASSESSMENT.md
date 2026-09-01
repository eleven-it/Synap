# 25 — Dependency Assessment

**Estado:** COMPLETE (Fase 25)  
**Fecha:** 25/08/2026

---

## Python (requirements.txt)

| Paquete | Versión | Uso | Riesgo |
|---------|---------|-----|--------|
| Django | 4.2 | Framework | OK — LTS |
| djangorestframework | latest | APIs | OK |
| psycopg2-binary | 2.9.9 | PostgreSQL | OK |
| mysqlclient | 2.2.7 | MySQL | OK |
| gunicorn | 21.2.0 | WSGI | OK |
| celery | ≥5.3,<6 | **Instalado sin worker** | Medio |
| django-redis | latest | Cache | OK |
| Pillow | 10.1.0 | Imágenes | Verificar CVEs |
| opencv-python-headless | ≥4.8,<5 | OCR | OK |
| pyafipws | local | AFIP | Mantener actualizado |
| pymssql | ≥2.2,<3 | Azure SQL | OK |
| webauthn | ≥2.0,<3 | Passkeys | OK |
| paramiko | ≥3.4,<4 | SFTP backup | OK |
| pytesseract | ≥0.3.10 | OCR | OK |
| reportlab | latest | PDF export | OK |
| openpyxl, pyxlsb | latest | Excel | OK |

### Eliminados (comentados)

openai, crewai, langchain — solo en support/backend

### Redundancias

- celery instalado pero no operacional
- django-allauth en requirements pero uso limitado

## Docker images

| Imagen | Versión | Nota |
|--------|---------|------|
| python | 3.10-slim | OK — considerar 3.12 |
| postgres | 13 | Considerar upgrade 15+ |
| redis | 6-alpine | OK |
| mysql | 5.7 (dev) | EOL — solo dev |

## JS (theme/)

- Node 20 LTS
- Tailwind 3.x via django-tailwind
- Alpine.js (CDN/embebido)

## Servicios externos

| Servicio | Criticidad | Fallback |
|----------|:----------:|----------|
| MySQL AdministraNET | **Crítica** | Ninguno |
| PostgreSQL | **Crítica** | Ninguno |
| Redis | Media | Degraded cache |
| AFIP/ARCA | Alta (TPV) | Sin FE |
| Tienda Nube API | Media | Sync pause |
| OpenAI/Anthropic | Baja | IA offline |

---

*Generado por auditoría READ ONLY.*
