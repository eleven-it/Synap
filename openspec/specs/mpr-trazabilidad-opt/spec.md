# mpr-trazabilidad-opt

## Purpose

Define el capability de **trazabilidad OPT drill-down** en el módulo MPR de Synap: servicios integrados de consulta cronológica que fusionan 6 fuentes (historico legacy, movimiento_stock, partes Django, transiciones, armados) y pantalla de drill-down por OPT con timeline vertical. Cierra el gap de enlace OPT↔parte mediante `MprParte.id_lista_produccion` y el gap de escritura al historico legacy desde OPP-parte (E4).

Esta capability es la Etapa 6 del refactor MPR multietapa (etapa FINAL del pipeline de producción 1-6).

Archivado desde el change SDD `mpr-pipeline-etapa6-trazabilidad-opt` (2026-07-03).

Documento operativo asociado: `docs/mpr/TRAZABILIDAD_OPT.md`.

---

## Requirements

### Requirement: Servicio construir_trazabilidad_opt

El sistema MUST proveer `construir_trazabilidad_opt(base_empresa, id_lista_produccion)` en `mpr/services.py` que retorne `{cabecera, eventos: [{tipo, fecha, descripcion, cantidad, operario, fuente}]}` ordenados cronológicamente. El servicio MUST integrar las siguientes fuentes: `lista_produccion_historico`, `movimiento_stock` (OPT/OPP), `MprParte/MprParteLinea/MprParteAjuste`, `MprTransicionLote`, `MprArmadoSurtidoMovimiento`, `MprImputacionArmado`.

#### Scenario: OPT liberada aparece como primer evento

- DADO id_lista_produccion=42 con evento OPT registrado en lista_produccion_historico
- CUANDO se llama construir_trazabilidad_opt(base, 42)
- ENTONCES el primer evento MUST ser tipo='OPT' con la fecha de liberación de la OPT

#### Scenario: Partes registrados aparecen con operario y turno

- DADO un MprParte con id_lista_produccion=42, turno=T1, id_operario=5
- CUANDO se llama construir_trazabilidad_opt(base, 42)
- ENTONCES los eventos de tipo='OPP' MUST incluir operario, turno y fecha_produccion

#### Scenario: Ajustes aparecen como eventos separados

- DADO un MprParteAjuste vinculado a un parte con id_lista_produccion=42
- CUANDO se llama construir_trazabilidad_opt(base, 42)
- ENTONCES MUST existir un evento tipo='OPP-ajuste' con el delta y motivo del ajuste

#### Scenario: Transiciones de lote aparecen

- DADO MprTransicionLote(id_articulo=A, tipo_origen='Produccion', tipo_destino='Planchado') para la OPT
- CUANDO se llama construir_trazabilidad_opt(base, 42)
- ENTONCES MUST existir evento tipo='Transicion' con tipo_origen y tipo_destino correctos

#### Scenario: Evento armado aparece

- DADO MprArmadoSurtidoMovimiento(id_lista_produccion=42, id_articulo_pack=P)
- CUANDO se llama construir_trazabilidad_opt(base, 42)
- ENTONCES MUST existir evento tipo='Armado' con código de movimiento

#### Scenario: Orden cronológico correcto

- DADO múltiples eventos de tipos distintos para id_lista=42
- CUANDO se llama construir_trazabilidad_opt(base, 42)
- ENTONCES los eventos MUST estar ordenados por fecha ASC

#### Scenario: Historico inexistente no rompe

- DADO que lista_produccion_historico no existe en la base MySQL
- CUANDO se llama construir_trazabilidad_opt(base, 42)
- ENTONCES el servicio MUST retornar eventos de otras fuentes sin lanzar excepción
- Y eventos sin fuente historico MUST estar marcados con fuente='movimiento_stock' o 'django'

---

### Requirement: Servicio construir_trazabilidad_articulo

El sistema MUST proveer `construir_trazabilidad_articulo(base_empresa, id_articulo, fecha_desde, fecha_hasta)` en `mpr/services.py` que retorne traza agregada por artículo en el rango de fechas. El servicio SHOULD reutilizar la lógica de integración de `construir_trazabilidad_opt`.

#### Scenario: Traza agrupada por OPT en rango de fechas

- DADO id_articulo=A con dos OPTs activas en fechas dentro del rango [F1, F2]
- CUANDO se llama construir_trazabilidad_articulo(base, A, F1, F2)
- ENTONCES MUST retornarse eventos de ambas OPTs, distinguibles por id_lista_produccion

#### Scenario: Eventos huérfanos marcados sin OPT

- DADO un movimiento en movimiento_stock tipo='OPP' sin id_lista identificable para id_articulo=A
- CUANDO se llama construir_trazabilidad_articulo(base, A, F1, F2)
- ENTONCES el evento MUST incluirse con id_lista_produccion=None y descripcion indicando 'sin OPT asociada'

---

### Requirement: Vista TrazabilidadOptView

El sistema MUST proveer `TrazabilidadOptView` accesible en `opt/<int:id_lista>/trazabilidad/` (prefijo `/mpr/`). La vista MUST usar `MprLoginRequiredMixin` y MUST filtrar por `base_empresa` de la sesión. El template MUST renderizar un timeline vertical cronológico usando `base_mpr.html` con Tailwind/Alpine.js.

#### Scenario: Usuario abre traza y ve eventos ordenados

- DADO usuario autenticado en base_empresa='EMP1', OPT id_lista=42 con eventos E1(OPT), E2(OPP), E3(Transicion)
- CUANDO el usuario navega a /mpr/opt/42/trazabilidad/
- ENTONCES la pantalla MUST mostrar E1, E2, E3 en orden cronológico ascendente
- Y las fechas MUST mostrarse en formato dd/MM/yyyy
- Y todos los textos visibles MUST estar en español

#### Scenario: Scoping base_empresa impide ver otra empresa

- DADO OPT id_lista=42 pertenece a base_empresa='EMP1'
- CUANDO usuario de base_empresa='EMP2' accede a /mpr/opt/42/trazabilidad/
- ENTONCES MUST retornarse 404 o redirect a error en español

---

### Requirement: Enganches de navegación

El sistema MUST agregar:
- Botón 'Ver trazabilidad' en el header de `opt_detail.html` que apunte a `opt/<id_lista>/trazabilidad/`
- Acción 'Ver trazabilidad' por fila de artículo en `tablero_produccion.html` que resuelva el id_lista_produccion del artículo activo

#### Scenario: Navegación desde opt_detail

- DADO usuario en /mpr/opt/42/
- CUANDO hace clic en 'Ver trazabilidad'
- ENTONCES navega a /mpr/opt/42/trazabilidad/ sin error

#### Scenario: Navegación desde tablero_produccion

- DADO fila del artículo A con id_lista_produccion=42 en tablero
- CUANDO el usuario hace clic en 'Ver trazabilidad' de esa fila
- ENTONCES navega a /mpr/opt/42/trazabilidad/

---

### Requirement: Nivel pack y detalle componentes

La cabecera del timeline MUST mostrar el artículo pack (nivel principal). El timeline SHOULD soportar expansión por componentes via Alpine.js (colapsable, cerrado por defecto).

#### Scenario: Pack en cabecera, componentes expandibles

- DADO OPT id_lista=42 con pack P y componentes C1, C2
- CUANDO el usuario abre /mpr/opt/42/trazabilidad/
- ENTONCES MUST mostrarse el pack P en cabecera del timeline
- Y los eventos de componentes MUST estar bajo sección expandible colapsada por defecto

---

### Requirement: No-funcionales trazabilidad

| Requisito | Norma |
|-----------|-------|
| Autenticación | Vista MUST usar MprLoginRequiredMixin |
| Scoping | Todas las queries MUST filtrar por base_empresa |
| Tipos AdministraNET | Reads MySQL legacy MUST usar to_int_or_none, to_date_or_none |
| Fechas UI | dd/MM/yyyy en todos los textos al usuario |
| Idioma | Mensajes y labels MUST estar en español |
| Canon UI | Template MUST extender mpr/base_mpr.html; NOT usar ventas/templates como referencia |
| Fallback | Si fuente MySQL falla o tabla ausente → continuar con fuentes disponibles; MUST NOT retornar 500 |

#### Scenario: Fallo de fuente MySQL no produce 500

- DADO que get_connection a lista_produccion_historico lanza OperationalError
- CUANDO se accede a /mpr/opt/42/trazabilidad/
- ENTONCES la vista MUST renderizar timeline con las fuentes disponibles sin HTTP 500
- Y MUST mostrarse aviso en español indicando que alguna fuente no está disponible

---

## Integration with Pipeline

Este capability integra el enlace OPT↔parte como campo de modelo (`MprParte.id_lista_produccion`) y cierra el gap de escritura al historico legacy desde `_registrar_asiento_fisico_opp_parte` (ver deltas en spec `mpr-opp-parte-produccion`).

La trazabilidad drill-down es la **última pieza del refactor MPR multietapa etapas 1-6** (E1 topología, E2 tablero, E3 turnos/roster, E4 OPP-parte, E5 transiciones+desmontaje, E6 trazabilidad). Ver nota de cierre en spec `mpr-pipeline-multietapa`.

---

## Notes

- **Etapa 6 (2026-07-03):** Migración 0013 aplicada (`MprParte.id_lista_produccion`). 322 tests mpr PASS (19 nuevos E6, 303 previos), 0 regresiones. Verify #1019 = PASS WITH WARNINGS (warnings no bloqueantes para E6.5): faltan tests conductuales con DB real para fuentes MprTransicionLote y MprArmadoSurtidoMovimiento en `construir_trazabilidad_opt`; REQ-TRZ-005 quedó como expandible por-evento (detalles técnicos), no sección separada de componentes; navegación desde tablero sin test automatizado.

- **Follow-ups pendientes E6.5:** 1) `id_lista_produccion` en `MprTransicionLote` (diferido de E6); 2) Tests conductuales fuentes 4/5 (transiciones y armados con objetos DB reales); 3) Sección de componentes agrupados en la traza (actualmente expandible por-evento); 4) Tests view-level de navegación desde opt_detail/tablero.

- **Deprecación ejecutar_opp:** `ejecutar_opp`, `ejecutar_opp_por_componentes` y `RegistrarOppView` marcados deprecated (E6). Eliminación efectiva + reescritura wizard paso 3 pospuestos hasta que el wizard se migre al patrón OPP-parte (capability pendiente fuera de E6).
