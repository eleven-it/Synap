# Resultado Fase 6 — Rollout y producción (plantilla operativa)

**Referencias:** DoD Fase 6, [master_execution_plan.md](compras/master_execution_plan.md) §7.

---

## 1. Feature flags

- **Global:** `FACTURA_COMPRA_POSTING_BACKEND` (`fake` | `noop` | `legacy` futuro), `FACTURA_COMPRA_LEGACY_SQL_ENABLED` (default **False**).
- **Por empresa/sucursal:** implementación recomendada — tabla o JSON en `Empresa` / config sistema que el adapter lea antes de ejecutar SQL; documentar en PR de activación.

---

## 2. Entorno preproducción

- Schema MySQL representativo del cliente (mismas versiones y triggers que prod).
- Dataset anonimizado mínimo para IT-LEG y prueba manual de analistas.

---

## 3. Pruebas con usuarios

| Caso | Resultado esperado |
|------|-------------------|
| Captura → revisión → aprobación stub | Flujo completo sin legacy |
| Activación posting real (pilot) | Un comprobante contado + uno crédito |
| Rollback simulado | Sin huella parcial en legacy |

**Registro:** mantener bitácora en herramienta de proyecto (no en este repo si política Staging sin docs).

---

## 4. Capacitación analistas

- Guía breve: pantalla `/compras/revision/<uuid>/`, permisos por rol, qué significa «posting simulado» vs real.
- Video o sesión grabada (opcional).

---

## 5. Monitoreo primera semana

| Métrica | Objetivo inicial (ejemplo) |
|---------|----------------------------|
| Volumen aprobaciones / día | Baseline acordado con producto |
| Tasa error posting | < umbral definido |
| Latencia p95 aprobación | Según SLA interno |

---

## 6. Plan rollback

1. Desactivar flag posting real / poner `noop` o `fake`.
2. Comunicar a operaciones y analistas.
3. Si hubo error a mitad de transacción legacy: seguir runbook DBA (fuera de Synap).

---

## 7. Métricas iniciales / feedback / issues (rellenar en cierre real)

- **Métricas iniciales:** _pendiente post-deploy._
- **Feedback usuarios:** _pendiente._
- **Issues detectados:** _pendiente._

**Sistema listo para producción** cuando producto + tech lead firmen criterio «listo para encender posting» con flags en modo seguro y DoD Fase 6 marcado.
