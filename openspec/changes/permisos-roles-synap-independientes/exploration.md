# Exploración — Permisos y roles Synap independientes de AdministraNET

**Cambio:** `permisos-roles-synap-independientes`  
**Modo:** Evolution Mode (nueva capa de persistencia; sin migrar VB6)  
**Fecha:** 08/07/2026

---

## 1. Objetivo de la exploración

Mapear el sistema de permisos runtime actual de Synap, identificar acoplamiento con tablas legacy compartidas con VB6 y definir la estrategia para independizar permisos/roles Synap sin romper auth ni Clavemenu.

---

## 2. Hallazgos principales

### 2.1 Doble sistema (uno inerte)

| Sistema | Ubicación | Estado runtime |
|---------|-----------|----------------|
| Modelos Django Rol/Permiso (legado Firebase) | `core/models` | **Inerte** — no usado en runtime |
| AdministraNETUser + SQL legacy | `core/services/administranet_permisos_usuario.py` | **Fuente única actual** |

### 2.2 Fuente de verdad runtime

- Función central: `get_permisos_totales_administranet` — lee `permiso_sistema JOIN permiso_sistema_puesto` + tablas legacy complementarias.
- Supervisor (`cod_usuario` especial) ⇒ permiso `{"*"}`.
- Wildcards por módulo: `modulo.*`.
- Verificación vía `decorators`, mixins, `context_processors`, menú dinámico.

### 2.3 Tablas legacy involucradas

| Tabla | Rol |
|-------|-----|
| `puestos` | Catálogo fijo de puestos VB6 (`idpuesto` reservados) |
| `permiso_sistema` | Catálogo permisos sistema (grupo 'Synap' inyectado post-login) |
| `permiso_sistema_puesto` | Asignación permiso↔puesto |
| `permisos` | Clavemenu VB6 — **se conserva lectura** |
| `permisos_sistema` | Reglas anchas TPV (límites descuento, etc.) — **se conserva lectura** |
| `usuarios` | Vincula usuario → `idpuesto` |

### 2.4 Inyección Synap (problema raíz)

- `core/services/sync_permisos_synap.py` ejecuta INSERT/UPDATE en `permiso_sistema` y `permiso_sistema_puesto` tras login.
- Semilla de keys: `core/constantes_permisos.py` → `PERMISOS_POR_MODULO`.
- `core/services/administranet_puestos.py` crea puestos con `MAX(idpuesto)+1`, mezclando IDs dinámicos con catálogo fijo VB6.

### 2.5 Hallazgo decisivo — tablas compartidas con VB6

Verificado en código VB6: `permiso_sistema` y `permiso_sistema_puesto` son **COMPARTIDAS** y escritas activamente por AdministraNET:

- `CargaPuesto.frm`
- `CargaPermiso_Sistema_Puesto_Valor.frm`
- `Funciones.bas`
- `IngresoUsuario.frm`

La inyección Synap contamina el catálogo que el supervisor edita desde VB6.

---

## 3. Decisión de arquitectura (Opción A — confirmada)

Crear tablas propias `synap_*` en MySQL por empresa vía catálogo central (`catalog.py`). **Sin escribir nunca** en tablas VB6. `idpuesto` permanece como ancla fija; no crear puestos nuevos en `puestos`.

Modelo propuesto:

| Tabla | Propósito |
|-------|-----------|
| `synap_permiso` | Catálogo dinámico (`key_permiso` único, módulo, nombre, activo) |
| `synap_rol` | Roles Synap (id autoincrement, nombre, es_sistema, activo) |
| `synap_rol_permiso` | M2M rol↔permiso |
| `synap_puesto_rol` | Mapeo `idpuesto` (valor fijo, sin FK VB6) → `synap_rol` |

Runtime futuro: `synap_puesto_rol → synap_rol_permiso → synap_permiso`.

Opción B (DB central Synap) **descartada**.

---

## 4. Riesgos detectados

1. **Divergencia dual-read** durante migración — mitigar con feature flag y tests de paridad.
2. **DDL por empresa** — provider idempotente aplicado en bootstrap/login o comando global.
3. **Filas residuales** grupo 'Synap' en legacy — limpieza controlada solo en P3.

---

## 5. Próximo paso SDD

**Propuesta** (`proposal.md`): fases P0–P3, capabilities, rollback y criterios de éxito.
