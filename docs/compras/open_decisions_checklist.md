# Checklist ejecutivo — decisiones abiertas (módulo compras / captura / posting)

**Uso:** revisión en kickoff de fase y antes de merge a entornos compartidos.  
**Actualizar:** al cerrar ítems (fecha + responsable).

**Leyenda bloqueo:**

- **B0** — No bloquea código Fase 1.
- **B1** — Bloquea Fase 2 en producción (puede usarse default dev).
- **B2** — Bloquea Fase 4 en ambiente que escribe legacy real.
- **B3** — Bloquea rollout (Fase 6).

| ID | Decisión | Impacto | Prioridad | Responsable típico | Bloqueo | Estado |
|----|----------|---------|-----------|-------------------|---------|--------|
| D-01 | Proveedor motor OCR (cloud/on-prem, idioma, coste) | Calidad extracción, coste, latencia, privacidad datos fiscales | Alta | Producto + Legal/IT | B1 prod / B0 dev | Pendiente |
| D-02 | Almacenamiento archivos (S3-compatible, disco, cifrado, retención) | Seguridad, backup, compliance | Alta | Infra + Producto | B1 prod | Pendiente |
| D-03 | Política duplicados **FM** (paridad VB6 vs default Synap) | Riesgo datos; ya acotado ADR-0004 | Media | Producto + Contabilidad | B0 (flag por empresa) | Pendiente |
| D-04 | Post-aprobación: ¿flujo CC / asiento visual en Synap obligatorio día 1? | Alcance Fase 4–5; *auditoría:* post-commit UI en VB6 | Media | Producto + Contador | B0 MVP | Pendiente |
| D-05 | Estrategia concurrencia `codmov` (timeout lock, reintentos) | Integridad numerador | Alta | Tech lead | B2 | Pendiente |
| D-06 | Entorno MySQL test (fixture mínima vs réplica anonimizada) | Velocidad CI vs fidelidad | Media | Tech lead + DBA | B2 merge posting real | Pendiente |
| D-07 | Feature flag `factura_compra_captura_enabled` ámbito (empresa/sucursal/usuario) | Rollout | Media | Producto | B3 | Pendiente |
| D-08 | Proveedor de cola (Celery/RQ/Django-Q) ya estándar en Synap | Arquitectura Fase 2 | Media | Tech lead | B0 si ya existe estándar | Pendiente |
| D-09 | Validación DDL columnas MySQL cliente vs `posting_sql_spec` | Fallos runtime posting | Alta | DBA + dev posting | B2 | Pendiente |
| D-10 | Comportamiento ante OCR parcial (umbral confianza por campo) | UX + reglas negocio Synap | Baja–Media | Producto + UX | B0 | Pendiente |

---

## Notas

- **D-01, D-02:** pueden resolverse con **decisión provisional desarrollo** (OCR mock + disco local) sin cerrar producción → marcar «Provisional OK» en columna estado.
- **D-03:** ADR-0004 ya define default técnico; falta **política producto** por empresa.
- **D-04:** *Inferencia desde auditoría:* VB6 abre UI contable tras commit; Synap puede diferir si producto acepta.

---

## Criterio de cierre Fase 0

Al menos: **D-08** alineado con repo; **D-01/D-02** con camino **dev** acordado; **D-07** propuesta escrita.

Ver también [master_execution_plan.md](master_execution_plan.md) y [definition_of_done_by_phase.md](definition_of_done_by_phase.md).
