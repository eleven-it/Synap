# Configuración y despliegue del frontend

## Variables de entorno

Solo se requieren variables mínimas; **no** se configuran claves operativas (canales, IA, storage, etc.) por `.env` en el frontend: esa configuración se hace desde la UI de Configuración (Admin) y se persiste en el **backend** (PostgreSQL, secretos cifrados). Support usa **un solo .env** en `support/.env`; debe incluir al menos `CONFIG_ENCRYPTION_KEY` (clave Fernet en base64) para cifrar tokens y API keys; ver `support/.env.example` y `support/docs/backend/API.md`.

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | URL base del backend **sin** `/api` al final. En desarrollo con proxy puede dejarse vacía para usar rutas relativas. | `http://localhost:8250` |
| `VITE_POLL_INTERVAL` | Opcional. Intervalo de polling en ms (p. ej. para refrescar detalle de caso). `0` = desactivado. | `10000` |

El frontend lee las variables desde **support/.env** (Vite tiene `envDir: ..` en `vite.config.ts`). Archivo de ejemplo: `support/.env.example`.

## Desarrollo local

```bash
cd support/frontend
npm install
# Crear support/.env desde support/.env.example si no existe; VITE_API_BASE_URL y demás se leen de ahí
npm run dev
```

- El servidor de Vite arranca por defecto en `http://localhost:3000`.
- En `vite.config.ts` está configurado un **proxy** de `/api` a `http://localhost:8250`. Si el backend corre en ese puerto, las peticiones desde el navegador van a mismo origen y el proxy reenvía a la API; en ese caso `VITE_API_BASE_URL` puede estar vacía.
- Si el backend está en otro host/puerto, definir `VITE_API_BASE_URL` para que el cliente apunte directamente (y configurar CORS en el backend para ese origen).

## Build de producción

```bash
cd support/frontend
npm run build
```

- Salida en `dist/`: `index.html` y assets en `dist/assets/`.
- El build usa la variable `VITE_API_BASE_URL` que exista en el momento del build; si está vacía, las peticiones serán relativas a `/api` (adecuado cuando el front se sirve desde el mismo dominio que la API).

## Despliegue

- **Opción 1 – Mismo dominio que la API:** Servir el contenido de `dist/` con nginx (o el backend con Whitenoise). La raíz sirve el SPA; `/api` se reenvía al backend. No hace falta configurar CORS para el mismo origen.
- **Opción 2 – Dominio distinto:** Definir `VITE_API_BASE_URL` en el build con la URL absoluta del backend. Configurar CORS en el backend para el origen del frontend y, si se usa sesión por cookie, SameSite y Secure según [backend/CONFIGURACION.md](../backend/CONFIGURACION.md) (seguridad SPA React).

## Scripts npm

| Script | Descripción |
|--------|-------------|
| `npm run dev` | Servidor de desarrollo (Vite). |
| `npm run build` | Compilación TypeScript y build de producción (Vite). |
| `npm run preview` | Sirve localmente la carpeta `dist/` para probar el build. |
| `npm run lint` | ESLint sobre `.ts` y `.tsx`. |

## Lazy-loading y bundles

- Las páginas (Dashboard, Casos, Empresas, etc.) se cargan con `React.lazy` y `Suspense`; cada una genera un chunk separado.
- El chunk principal incluye React, Router, MUI, TanStack Query, etc. Si el tamaño del bundle es preocupación, se puede aplicar code-splitting adicional (p. ej. por sección de Configuración).

## Accesibilidad y UX

- Tema MUI con contraste por defecto; foco visible y estructura semántica.
- Skeletons durante la carga de listas y detalle.
- Toasts (notistack) para éxito y error en mutaciones.
- Empty states cuando no hay datos; mensajes de error con posibilidad de reintentar (recargar o reejecutar la query).
