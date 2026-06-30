# E2E Playwright — MPR

Pruebas end-to-end del flujo **demanda → OPT → OPP** con capturas para el manual HTML.

## Requisitos

- Synap corriendo en `http://localhost:8000` (contenedor `Synap_app`).
- `ENVIRONMENT=development` o `DEBUG=True` (comando `crear_sesion_e2e`).
- Node.js 18+.

## Instalación

```bash
cd tests/e2e/mpr
npm install
npx playwright install chromium
```

## Ejecutar

```bash
cd tests/e2e/mpr
SYNAP_BASE_EMPRESA=administranet96 SYNAP_COD_USUARIO=Supervisor MPR_E2E_CANTIDAD=10 npm test
```

Modo visible:

```bash
npm run test:headed
```

## Salidas

| Artefacto | Ubicación |
|-----------|-----------|
| Capturas PNG | `docs/mpr/e2e/capturas/NN-slug.png` |
| Registro paso a paso | `docs/mpr/e2e/REGISTRO_FLUJO_E2E.md` |
| Manual HTML visual | `docs/mpr/e2e/MANUAL_USUARIO_MPR.html` |
| Reporte HTML | `tests/e2e/mpr/playwright-report/` |

## Variables

| Variable | Default | Uso |
|----------|---------|-----|
| `SYNAP_BASE_URL` | `http://localhost:8000` | URL base |
| `SYNAP_BASE_EMPRESA` | `administranet96` | Empresa MySQL |
| `SYNAP_COD_USUARIO` | `Supervisor` | Usuario sesión E2E |
| `MPR_E2E_CANTIDAD` | `10` | Unidades a fabricar en demanda |

## Sesión sin contraseña (solo dev)

```bash
docker exec Synap_app python manage.py crear_sesion_e2e --cod-usuario=Supervisor --base-empresa=administranet96
```
