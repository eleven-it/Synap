# Delta for mpr-opp-parte-produccion

## MODIFIED Requirements

### Requirement: Modelos de Parte de Producción

El sistema MUST persistir partes en MySQL:

- **`mpr_parte`**: PK `id_mpr_parte` AI; `uuid_parte` UNIQUE opcional; `fecha_produccion`; FK `id_mpr_turno`; `id_usuario`; `registrado_en`; `notas`; `movimiento_fisico_ok`; `id_lista_produccion` NULL (legacy OPT / NULL E8).
- **`mpr_parte_linea`**: FK `id_mpr_parte` CASCADE; `id_articulo` componente; `id_operario`; `operario_nombre`; `cantidad`; UNIQUE `(id_mpr_parte, id_articulo, id_operario)`.
- **`mpr_parte_ajuste`**: PK AI; `uuid_ajuste` opcional; FK `id_mpr_parte` RESTRICT; `delta`; `motivo`; `ajuste_fisico_ok`.

MUST NOT usar modelos Django Postgres ni columna `base_empresa` en tablas. Asiento físico MySQL (`movimiento_stock`, `stock_deposito`) MUST permanecer sin cambio semántico.

(Previously: modelos Django `MprParte`/`MprParteLinea`/`MprParteAjuste` en Postgres con UUID PK y `base_empresa`.)

#### Scenario: Crear parte con línea respeta unique constraint

- DADO turno T1 en `mpr_turno`, fecha=04/07/2026
- CUANDO se inserta `mpr_parte` y línea (art=10, op=5, cant=8)
- ENTONCES MUST persistir sin error
- Y segundo INSERT con mismo (parte, art, op) MUST fallar por UNIQUE

#### Scenario: Múltiples partes por mismo turno y fecha

- DADO dos cabeceras `mpr_parte` mismo turno y fecha
- CUANDO se guardan
- ENTONCES ambas MUST persistir (sin UNIQUE en cabecera)

---

### Requirement: Configuración bloqueo Fabricando — mpr_config

El flag `bloquear_parte_supera_fabricando` MUST leerse desde **`mpr_config`** MySQL (singleton). MUST NOT usarse `MprEmpresaConfig` Postgres ni filtrar por `base_empresa` en SQL.

(Previously: `MprEmpresaConfig.objects.get_or_create(base_empresa=...)`.)

#### Scenario: Bloqueo activo desde mpr_config

- DADO `mpr_config.bloquear_parte_supera_fabricando=1`
- CUANDO parte supera Fabricando
- ENTONCES MUST rechazar registro con mensaje español

---

### Requirement: No-funcionales Transversales

| Requisito | Norma |
|-----------|-------|
| Scoping | Queries MUST usar BD de `get_connection(base_empresa)`; MUST NOT columna `base_empresa` en tablas |
| Tipos | MUST usar `administranet_types` en lecturas legacy |
| Fechas UI | dd/MM/yyyy |
| Idioma | Español |

(Previously: filtrar ORM por `base_empresa`.)

#### Scenario: Aislación por base de datos

- DADO partes en BD `administranet92` y BD `administranet89`
- CUANDO se listan partes con conexión a `administranet92`
- ENTONCES MUST retornarse solo filas de esa BD

---

## ADDED Requirements

### Requirement: Compatibilidad URL uuid_parte

Durante transición, MUST resolverse `/mpr/parte/<uuid>/` vía columna `uuid_parte` en MySQL.

#### Scenario: Redirect UUID legacy

- DADO parte con `uuid_parte` conocido
- CUANDO usuario accede por URL UUID
- ENTONCES MUST mostrarse el parte correcto sin error 404
