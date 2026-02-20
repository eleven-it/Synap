# Política de documentación

## Regla: todo desarrollo debe actualizar la documentación

A partir de este momento, **todo cambio de desarrollo (features, refactors, correcciones de comportamiento, nuevos módulos o integraciones) debe incluir la actualización de la documentación** en `docs/`.

### Objetivo

- Dar **contexto** a distintas sesiones de trabajo y a equipos multidisciplinarios.
- Mantener una **fuente única** de verdad sobre decisiones, flujos y uso de módulos.
- Facilitar onboarding y mantenimiento.

### Qué documentar

- **Nuevas funcionalidades:** descripción breve, dónde está el código, cómo se usa (y si aplica, parámetros o APIs).
- **Cambios de comportamiento:** qué cambió, por qué y dónde (archivo o módulo).
- **Decisiones de diseño o arquitectura:** en el doc del módulo o en `docs/general/` si afecta al proyecto.
- **APIs o contratos:** endpoints, parámetros, respuestas (en `docs/reports/`, `docs/self_checkout/`, etc., según módulo).
- **Configuración o despliegue:** en `docs/general/` (ej. Docker, instalación mínima) o en el módulo correspondiente.

### Dónde documentar

- **General (plan, flujo, instalación, módulos globales):** `docs/general/`
- **Módulo Reportes:** `docs/reports/`
- **Módulo Self-checkout / TPV / caja:** `docs/self_checkout/`
- **Login / sesión / shell:** `docs/login/` o `docs/general/` según alcance.

Los README en la raíz (`README_REPORTS.md`, `README_INSTALLATION.md`) se mantienen como punto de entrada; el detalle vive en `docs/`.

### En el flujo de trabajo

- Incluir en el **mismo commit** (o en un commit inmediato) los cambios de código y los de documentación.
- En **code review**, comprobar que la documentación afectada esté actualizada.
- Los **agentes y asistentes** de desarrollo deben usar y actualizar `docs/` según esta política (ver [.cursorrules](../../.cursorrules) y [docs/README.md](../README.md)).
