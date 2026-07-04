# Pipeline MPR — Etapa 1: Topología de Etapas y Modelo de Estados

**Versión:** 1.0  
**Change:** `mpr-pipeline-etapa1-topologia-estados`  
**Implementado en:** Etapa 1 del refactor MPR (julio 2026)  
**Archivos nuevos:** `mpr/pipeline.py`, `mpr/tests/test_pipeline_etapa1.py`  
**Archivos modificados:** `mpr/services.py`, `mpr/views.py`, `core/services/legacy_mysql_schema/catalog.py`

---

## Resumen

Esta etapa formaliza el contrato de estados y transiciones del pipeline MPR como módulo puro (`mpr/pipeline.py`), agrega la constante `TIPO_MPR_PLANCHADO` al catálogo de tipos, y expone el getter correspondiente. Todos los cambios son **aditivos**: el wizard, `ejecutar_liberar_opt` y los automatismos existentes permanecen intactos.

---

## Modelo de Etapas

El pipeline MPR tiene **8 etapas**: 2 virtuales (ledger) y 6 físicas (stock en `stock_deposito`).

### Orden canónico (`ORDEN_ETAPAS_MPR`)

| # | Nombre | Tipo | Semántica |
|---|--------|------|-----------|
| 1 | **Pendiente de producir** | Virtual (derivado) | `max(0, Demanda − Enviado − Total)` |
| 2 | **Enviado a producción** | Virtual (ledger) | `OPT acumulado liberado − OPP acumulado registrado` |
| 3 | **Producción** | Físico | Nace al registrar OPP; `tipo_mpr=Produccion` |
| 4 | **Planchado** | Físico | Inspección aprobatoria desde Producción; `tipo_mpr=Planchado` |
| 5 | **2da Selección** | Físico | Desde Planchado; `tipo_mpr=2daSeleccion` |
| 6 | **Semi Elaborado** | Físico | Desde Planchado; `tipo_mpr=SemiElaborado` |
| 7 | **Terminado** | Físico | Destino final del armado; `tipo_mpr=Terminado` |
| 8 | **Desperdicio** | Físico (terminal) | Desde Producción por inspección reprobatoria; `tipo_mpr=Scrap`. No suma al Total |

### Diagrama de flujo

```
┌─────────────────────────────────────────────────────────────────────┐
│                       PIPELINE MPR                                  │
│                                                                     │
│  [VIRTUAL]              [FÍSICO — stock_deposito por tipo_mpr]      │
│                                                                     │
│  Pendiente ──(a)──► Enviado ──(b: OPP)──► Producción               │
│  (derivado)         (virtual)             │        │                │
│                                           │(c)     │(c)             │
│                                           ▼        ▼                │
│                                        Planchado  Desperdicio       │
│                                           │       (terminal)        │
│                                      (d) ├──────► 2da Selección ──┐ │
│                                          └──────► Semi Elaborado ─┤ │
│                                                                (e) ▼ │
│                                                            Terminado │
│                                                            (terminal)│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Transiciones Legales (`TRANSICIONES_LEGALES`)

| ID | Origen | Destino | Descripción |
|----|--------|---------|-------------|
| (a) | Pendiente | Enviado | Liberación de OPT (derivado, sin stock físico) |
| (b) | Enviado | Producción | Registro de OPP → stock físico en `tipo_mpr=Produccion` |
| (c) | Producción | Planchado | Inspección aprobatoria |
| (c) | Producción | Desperdicio | Inspección reprobatoria |
| (d) | Planchado | 2da Selección | Armado parcial hacia 2da selección |
| (d) | Planchado | Semi Elaborado | Armado parcial hacia semi elaborado |
| (e) | 2da Selección | Terminado | Armado final |
| (e) | Semi Elaborado | Terminado | Armado final |

**Transiciones ilegales** (rechazadas por `validar_transicion`):
- Producción → Terminado (salto de etapa)
- 2da Selección → Producción (reversa)
- Desperdicio → cualquiera (terminal)
- Terminado → cualquiera (terminal)
- Cualquier par no listado en `TRANSICIONES_LEGALES`

---

## Fórmulas Derivadas

### Total por artículo

```
Total = Σ stock_deposito(id_articulo, id_deposito)
          WHERE id_deposito ∈ depósitos con tipo_mpr ∈ TIPOS_QUE_SUMAN_STOCK
          AND suma_stock = 'Si'
```

`TIPOS_QUE_SUMAN_STOCK = {Produccion, Planchado, 2daSeleccion, SemiElaborado, Terminado}`  
*(Desperdicio/Scrap excluido explícitamente)*

### Enviado a producción (virtual)

```
Enviado_virtual = OPT_acumulado_liberado(id_articulo) − OPP_acumulado_registrado(id_articulo)
```

Ledger sin movimiento en `stock_deposito`. El desmontaje del automatismo en `ejecutar_liberar_opt()` está diferido a **etapa 5**.

### Pendiente de producir (derivado)

```
Pendiente = max(0, Demanda_componente − Enviado_virtual − Total)
```

`Demanda_componente` = explosión BOM del pack (pedidos + reserva) neteada contra `stock_terminado` del pack.  
La reserva se mantiene a nivel PACK, no a nivel componente individual (REQ-019).

---

## Nueva Etapa: Planchado

### Constante

```python
# mpr/services.py
TIPO_MPR_PLANCHADO = "Planchado"
```

### Semántica

- Recibe piezas desde Producción por inspección aprobatoria.
- Puede transferir a 2da Selección o Semi Elaborado.
- **No** es destino de OPP: `TIPO_MPR_PLANCHADO not in TIPOS_MPR_OPP`.
- **Sí** suma al Total: `TIPO_MPR_PLANCHADO in TIPOS_QUE_SUMAN_STOCK`.

### Getter de depósito

```python
# mpr/services.py
def get_deposito_planchado_mpr(base_empresa: str) -> Optional[int]:
    """Depósito de planchado (tipo_mpr=Planchado): etapa de inspección aprobatoria desde Producción."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_PLANCHADO)
```

### Configuración UI

Incluida en `TIPOS_MPR_CON_ETIQUETA` en `mpr/views.py`:
```python
(TIPO_MPR_PLANCHADO, "Planchado"),   # entre Producción y Semi Elaborado
```

---

## API del Módulo `mpr/pipeline.py`

### Constantes exportadas

| Nombre | Tipo | Descripción |
|--------|------|-------------|
| `ESTADO_VIRTUAL_PENDIENTE` | `str` | `"Pendiente"` |
| `ESTADO_VIRTUAL_ENVIADO` | `str` | `"Enviado"` |
| `ORDEN_ETAPAS_MPR` | `tuple[str, ...]` | 8 etapas en orden canónico |
| `TIPOS_QUE_SUMAN_STOCK` | `frozenset[str]` | 5 etapas físicas que suman al Total |
| `TRANSICIONES_LEGALES` | `dict[str, frozenset[str]]` | Grafo de transiciones permitidas |

### Funciones exportadas

#### `es_transicion_legal(origen, destino) -> bool`

Consulta `TRANSICIONES_LEGALES`. Sin I/O.

#### `validar_transicion(origen, destino, cantidad, saldo_origen) -> tuple[bool, str | None]`

Valida legalidad + disponibilidad de saldo. Retorna `(True, None)` si válida, `(False, mensaje)` si no.

---

## Tests

Archivo: `mpr/tests/test_pipeline_etapa1.py`  
Comando: `docker exec Synap_app python manage.py test mpr.tests.test_pipeline_etapa1`

| Clase | Cobertura |
|-------|-----------|
| `TestConstantesPlanchado` | REQ-001, REQ-003, REQ-004, REQ-007 |
| `TestGetDepositoPlanchado` | REQ-002 (con mocks MySQL) |
| `TestEsTransicionLegal` | REQ-010 a REQ-015 (transiciones legales e ilegales) |
| `TestValidarTransicion` | REQ-015, REQ-016 (saldo, cantidad, legalidad) |
| `TestOrdenCanonicoYSumaStock` | REQ-005, REQ-018 |

Todos los tests son puros: no requieren base de datos MySQL real.

---

## Rollback

1. Revertir las 3 líneas añadidas en `mpr/services.py` (`TIPO_MPR_PLANCHADO`, tupla `validos`, `get_deposito_planchado_mpr`).
2. Revertir entrada `(TIPO_MPR_PLANCHADO, "Planchado")` en `TIPOS_MPR_CON_ETIQUETA` en `mpr/views.py`.
3. Revertir COMMENT en `core/services/legacy_mysql_schema/catalog.py`.
4. Eliminar `mpr/pipeline.py` y `mpr/tests/test_pipeline_etapa1.py`.

Sin DDL nuevo ni migraciones de datos.

---

## Fuera de Alcance (Etapas Futuras)

| Funcionalidad | Etapa |
|---------------|-------|
| Tablero UI consolidado de estados | 2 |
| Modelos Django Turno/Roster | 3 |
| OPP como parte de producción (MprParte) | 4 |
| Transiciones por lote, desmontaje de automatismos | 5 |
| Trazabilidad OPT drill-down | 6 |
