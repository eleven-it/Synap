# Exploración: Auditoría y recálculo de contabilidad (cont_*)

## Contexto

Auditoría de reversa de los formularios VB6 `Cont_*` de AdministraNET (módulo contabilidad)
detectó 50 hallazgos (bugs, inconsistencias, riesgos de integridad) en los procesos de
imputación. Se necesita un sistema en Synap que primero **audite en solo lectura** los datos
del MySQL legacy y luego permita **corregir/recalcular** de forma controlada.

## Documentos base (fuente de verdad de esta exploración)

- `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` — inventario de 25 formularios,
  modelo de datos y 50 hallazgos categorizados (crítico/alto/medio/diseño) con referencias
  archivo:línea y priorización de refactor.
- `docs/general/PROPUESTA_ARQUITECTURA_AUDITORIA_RECALCULO_CONTABILIDAD_SYNAP.md` — propuesta de
  arquitectura: motor de auditoría (lectura), motor de corrección (dry-run + escritura con
  salvaguardas) y políticas contables como configuración por empresa.

## Hallazgos clave que motivan el cambio

- Transacciones colgadas en `Exit Sub` sin `RollbackTrans` (Cont_CargaAsientoM.frm).
- `saldo_pc_temp` usado sin control de NULL → re-imputación de saldos incorrecta.
- `generar_asiento_cont()` no transaccional; `Balancea_asiento()` solo corrige ±0.01.
- `id_concepto_asiento + 1` en contra-asientos en vez de `id_concepto_anul`.
- `GeneraAsientoInflacion()` con loop de acumulación roto y conceptos hardcodeados.
- `Truncar()` y formateo de fechas dependientes del locale.
- Prefijos de cuenta hardcodeados ('1%','2%','3%','4%','41','42').
- Concurrencia optimista débil en `nro_asiento_ejercicio`.

## Anclaje Synap (componentes reutilizables)

- Pool MySQL legacy: `get_mysql_pool()` (patrón en `reports/services/reconciliation_*`).
- App `legacy_db` para escrituras legacy (`legacy_db/services/imputaciones_service.py`).
- Tipos legacy: `core.utils.administranet_types`.
- Router/DB y `DEFAULT_BASE_EMPRESA` en `django_project/settings.py`.
- Canon UI: reportes `/reports/dashboard/<slug>/` y MPR `/mpr/...`.

## Enfoque recomendado

Dos motores en fases:
1. **Auditoría (solo lectura)** — nueva app `contabilidad_audit` con catálogo de checks
   deterministas contra el MySQL legacy; no escribe nada.
2. **Corrección/recálculo** — servicio en `legacy_db` con dry-run, backup, transacciones,
   detección de concurrencia, log de auditoría y orden seguro de ejecución.

Políticas contables (tratamiento de anulados, política del centavo, prefijos de cuenta,
ejercicios cerrados, alcance del recompute, tolerancia decimal) modeladas como
**configuración por empresa** en la DB de Synap, con snapshot (`config_hash`) por corrida
para reproducibilidad.

## Decisión de alcance para el change

Priorizar la **Fase 1 (auditoría en solo lectura)** como entregable implementable primero;
la corrección en DB queda especificada pero detrás de salvaguardas y `ENVIRONMENT=production`.
