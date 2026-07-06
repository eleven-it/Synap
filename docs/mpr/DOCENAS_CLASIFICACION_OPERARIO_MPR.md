# Docenas operativas y clasificación por operario fabricante (MPR)

**Change OpenSpec:** `openspec/changes/mpr-docenas-clasificacion-operario/`  
**Estado:** Implementado en Desarrollo — aplicar migración MySQL en cada base empresa.  
**Fecha:** 08/07/2026

---

## Resumen ejecutivo

Dos mejoras coordinadas para alinear MPR con la planta textil:

1. **Presentación en docenas** por defecto en tablero, envío, parte y clasificación (persistencia en unidades).
2. **Clasificación por operario que fabricó**, con reparto Semi elaborado / 2da selección / Scrap y reporte de rendimiento ampliado.

---

## Decisiones de producto

| Tema | Decisión |
|------|----------|
| Default presentación | Docenas en flujo operativo |
| Toggle | Sesión `mpr_presentacion_cantidad` |
| Divisor componentes | 12 u./docena |
| Filas clasificación | (artículo × operario), solo pendiente > 0 |
| Alcance pendiente | Fecha + turno del clasificador |
| Arrastre | Sección separada turnos anteriores |
| Clasificación parcial | Sí |
| Parte sin operario | Bloquear clasificación por rendimiento |
| Reportes | Mismo release que la grilla |
| Ledger | `id_operario` = fabricante; `id_usuario` = quien guardó |

---

## Flujo en planta

```text
Parte (por operario) → Stock Producción agregado
                    → Clasificador revisa bultos por operario
                    → Clasificación (semi / 2da / scrap) con id_operario fabricante
                    → Reporte rendimiento por operario
```

---

## Artefactos SDD

| Documento | Ruta |
|-----------|------|
| Exploración | `openspec/changes/mpr-docenas-clasificacion-operario/exploration.md` |
| Propuesta | `openspec/changes/mpr-docenas-clasificacion-operario/proposal.md` |
| Diseño UX | `openspec/changes/mpr-docenas-clasificacion-operario/design.md` |
| Tasks | `openspec/changes/mpr-docenas-clasificacion-operario/tasks.md` |
| Spec docenas | `specs/mpr-presentacion-docenas-operativa/spec.md` |
| Spec clasificación | `specs/mpr-clasificacion-operario-fabricante/spec.md` |
| Spec reporte | `specs/mpr-reporte-rendimiento-operario/spec.md` |

---

## Cambio de esquema

`mpr_transicion_lote`:

- `id_operario` INT NULL — operario fabricante
- `operario_nombre` VARCHAR — snapshot al guardar

Migración vía `core/services/legacy_mysql_schema/catalog.py`.

---

## P1 completado

- Toggle supervisor **Ver roster completo** en clasificación (filas completadas solo lectura).
- Hub reportes MPR: default **docenas** (GET, sesión operativa o fallback).
- Reporte operario: gráfico apilado **semi · 2da · scrap** (`hbar_stacked`).
