# mpr-pipeline-multietapa

## Purpose

Define el comportamiento canónico del **pipeline de producción multietapa MPR** en Synap: topología de etapas físicas y virtuales, modelo de estados, configuración de depósitos por `tipo_mpr`, tablero consolidado por artículo/componente y explosión BOM de demanda.

Archivado desde el change SDD `mpr-pipeline-etapa2-tablero-consolidado` (2026-07-02).

Documento operativo asociado: `docs/mpr/TABLERO_CONSOLIDADO.md`.

> **Delta Etapa 10 (`mpr-pipeline-etapa10-clasificacion-consolidada`, 2026-07-03):**
> Se **elimina la etapa "Planchado"** del pipeline (no es depósito ni deja stock; es un
> momento dentro de la producción). Consecuencias normativas que **prevalecen** sobre el texto
> histórico de este spec:
> - `ORDEN_ETAPAS_MPR` pasa a **7 etapas** (2 virtuales + 5 físicas), sin Planchado.
> - `TIPOS_QUE_SUMAN_STOCK` = {Producción, 2da Selección, Semi Elaborado, Terminado} (sin Planchado).
> - El tablero muestra **9 columnas** de pipeline (se retira la columna «Planchado»).
> - Transiciones legales desde Producción: `→ {SemiElaborado | 2daSeleccion | Scrap}`.
> - El tablero expone **un único** botón global "Clasificación de producción"
>   (`mpr:clasificacion_produccion`); se retiran los botones "Inspección"/"Clasificación" de E9.
> Los escenarios y requisitos que mencionan Planchado como columna/etapa quedan **obsoletos**.

---

## Requirements

### Requirement: Tablero Consolidado por Artículo/Componente

El sistema MUST proveer una vista "Tablero de producción" accesible desde la URL `mpr/tablero-produccion/` que muestre un tablero consolidado con filas por ARTÍCULO/componente (no por pack) y 10 columnas canónicas del pipeline: Artículo, Pendiente de producir, Enviado a producción, Producción, Planchado, 2da Selección, Semi Elaborado, Desperdicio, Terminado, Total.

#### Scenario: Acceso a tablero de producción

- DADO un usuario autenticado con permisos MPR
- CUANDO accede a la URL `mpr/tablero-produccion/`
- ENTONCES MUST visualizar un tablero con las 10 columnas canónicas
- Y cada fila MUST representar un artículo/componente único
- Y NO MUST mostrar filas a nivel pack

#### Scenario: Columnas del tablero en orden canónico

- DADO el tablero de producción renderizado
- CUANDO se inspeccionan las columnas de la tabla
- ENTONCES MUST aparecer en el orden: Artículo (col 1), Pendiente (col 2), Enviado (col 3), Producción (col 4), Planchado (col 5), 2da Selección (col 6), Semi Elaborado (col 7), Desperdicio (col 8), Terminado (col 9), Total (col 10)
- Y la columna Artículo MUST estar fijada (sticky-left) al hacer scroll horizontal

---

### Requirement: Consolidación por Componente (Explosión BOM)

El tablero MUST consolidar la demanda por artículo/componente mediante explosión BOM: si un pack P tiene demanda (pedido + reserva) y su BOM incluye componente C con cantidad Q, la demanda de C MUST incrementarse en `(cantidad_a_fabricar_pack_P) × Q`.

#### Scenario: Demanda de componente desde un pack

- DADO un pack P con demanda de 10 unidades (cantidad_a_fabricar=10)
- Y la BOM de P incluye componente C con cantidad 2 por pack
- CUANDO se calcula la demanda consolidada
- ENTONCES el componente C MUST aparecer en el tablero con demanda de 20 unidades (10 × 2)

#### Scenario: Demanda de componente desde múltiples packs

- DADO un pack P1 con demanda de 10 unidades y BOM que incluye C (cantidad 2)
- Y un pack P2 con demanda de 5 unidades y BOM que incluye C (cantidad 3)
- CUANDO se calcula la demanda consolidada
- ENTONCES el componente C MUST aparecer en el tablero con demanda de 35 unidades (10×2 + 5×3)

#### Scenario: Pack sin BOM no aporta componentes

- DADO un pack P sin BOM configurada (artículo no existe en ABM o BOM vacía)
- CUANDO se calcula la demanda consolidada
- ENTONCES el pack P NO MUST aportar componentes al tablero
- Y NO MUST generar error

#### Scenario: Artículo sin demanda no aparece

- DADO un artículo A que NO es componente de ningún pack con demanda
- Y el artículo A tiene stock en alguna etapa física
- CUANDO se renderiza el tablero
- ENTONCES el artículo A NO MUST aparecer en el tablero (solo se muestran artículos con demanda derivada)

---

### Requirement: Columnas Físicas desde Stock por Tipo MPR (Producción desde OPP-parte, Etapa 5)

Las columnas físicas (Producción, Planchado, 2da Selección, Semi Elaborado, Desperdicio, Terminado) MUST reflejar el saldo de `stock_deposito` agrupado por artículo y `tipo_mpr` del depósito correspondiente. El sistema MUST obtener estos datos mediante una consulta pivote única que agrupe por `id_articulo` y `tipo_mpr`.

**Desde Etapa 5:** La columna Producción se alimenta EXCLUSIVAMENTE del asiento físico ejecutado por `registrar_parte_produccion` (OPP-parte). `ejecutar_liberar_opt` (OPT) NO MUST escribir stock en depósito Producción; solo genera el comprobante virtual MSTOCK tipo_mov='OPT' y actualiza `lista_produccion_agrupada` (campos `en_proceso_produccion`, `codigo_movimiento_opt`, `cantidad_asignada_opt`). Esto elimina el doble conteo conceptual: Enviado y Producción ahora son complementarios (Enviado = unidades comprometidas/encoladas AÚN no nacidas físicamente; Producción = unidades ya nacidas físicamente vía partes de producción).

#### Scenario: Stock físico en múltiples etapas

- DADO un artículo A con stock_deposito[Produccion] = 10, stock_deposito[Planchado] = 15, stock_deposito[2daSeleccion] = 5, stock_deposito[Terminado] = 20
- CUANDO se renderiza el tablero
- ENTONCES la fila de A MUST mostrar: Producción = 10, Planchado = 15, 2da Selección = 5, Semi Elaborado = 0, Desperdicio = 0, Terminado = 20

#### Scenario: Stock en depósito anulado no cuenta

- DADO un artículo A con stock_deposito en depósito D (tipo_mpr=Produccion)
- Y el depósito D tiene `anulado='Si'`
- CUANDO se calcula el stock físico
- ENTONCES el stock del depósito D NO MUST sumarse a la columna Producción

#### Scenario: Liberar OPT NO modifica stock Producción (Etapa 5)

- DADO stock_deposito[A, deposito_produccion]=0
- CUANDO ejecutar_liberar_opt para OPT del artículo A
- ENTONCES stock_deposito[A, deposito_produccion] MUST permanecer en 0
- Y movimiento_stock tipo_mov='OPT' MUST existir (comprobante virtual conservado)
- Y lista_produccion_agrupada.en_proceso_produccion='Si', codigo_movimiento_opt>0 MUST ser True

#### Scenario: Producción sube al registrar parte (Etapa 5)

- DADO stock_deposito[C, deposito_produccion]=0, OPP_parte_acum(P)=0
- CUANDO registrar_parte_produccion(pack=P, qty=20), _explode retorna {C: 20}
- ENTONCES stock_deposito[C, deposito_produccion]=20
- Y Enviado(P) = max(0, OPT_liberado_acum − 20)

---

### Requirement: Cálculo de Total (Suma de Físicas con suma_stock, Excluye Desperdicio)

La columna Total MUST calcularse como la suma del saldo **de los depósitos con `suma_stock='Si'`** de los tipos MPR en `TIPOS_QUE_SUMAN_STOCK` (Producción, Planchado, 2da Selección, Semi Elaborado, Terminado), excluyendo explícitamente Desperdicio (tipo_mpr=Scrap con `suma_stock='No'`).

**Importante:** El Total respeta el flag `deposito.suma_stock` por depósito individual: si un depósito de una etapa que normalmente integra el Total tiene configurado `suma_stock='No'`, su saldo se muestra en la columna correspondiente a esa etapa pero **NO** se cuenta en el cálculo del Total.

#### Scenario: Total con múltiples etapas

- DADO un artículo A con Producción = 10, Planchado = 15, 2da Selección = 5, Semi Elaborado = 0, Desperdicio = 8, Terminado = 20
- CUANDO se calcula Total
- ENTONCES MUST ser 50 (10+15+5+0+20, excluyendo Desperdicio=8)

#### Scenario: Desperdicio no suma al Total

- DADO un artículo A con Desperdicio = 10
- Y todas las etapas con suma_stock='Si' con stock = 0
- CUANDO se calcula Total
- ENTONCES MUST ser 0 (Desperdicio NO se suma)

#### Scenario: Total respeta flag suma_stock por depósito

- DADO un artículo A con saldo de 20 unidades en un depósito de tipo_mpr 'Produccion' configurado con `suma_stock='No'`
- Y 30 unidades en otro depósito de tipo_mpr 'Produccion' con `suma_stock='Si'`
- CUANDO se calcula Total
- ENTONCES MUST incluir solo las 30 unidades del depósito con `suma_stock='Si'`
- Y la columna Producción MUST mostrar 50 (suma de ambos depósitos)
- PERO el Total MUST contar solo 30 (respetando el flag por depósito)

---

### Requirement: Columna Enviado a Producción (Virtual, Fórmula Definitiva E7 — dos fuentes)

La columna "Enviado a producción" MUST calcularse como la suma de dos fuentes sin doble conteo:

```
Enviado_OPT[comp]     = explosión BOM de max(0, OPT_lib_acum[pack] − OPP_parte_acum[pack])
Enviado_tablero[comp] = max(0, SUM(MprEnvioProduccion[comp, anulado=False]) − stock_produccion[comp])
Enviado[comp]         = Enviado_OPT[comp] + Enviado_tablero[comp]
```

donde:
- `OPT_lib_acum[pack]` = cantidad comprometida/liberada registrada en `lista_produccion_agrupada` o equivalente (tabla OPT).
- `OPP_parte_acum[pack]` = suma de las cantidades registradas en partes de producción para ese pack: `SUM(MprParteLinea.cantidad + Σ MprParteAjuste.delta)` (ver capability `mpr-opp-parte-produccion`, Etapa 4).
- `MprEnvioProduccion[comp]` = ledger de envíos directos a producción desde el tablero, nivel componente (ver capability `mpr-envio-produccion-tablero`, Etapa 7).
- `stock_produccion[comp]` = saldo físico del componente en el depósito tipo MPR "Produccion" (calculado en `_pivot_stock_por_tipo_mpr`).

El sistema MUST integrar `_query_enviado_tablero_componente` como paso 7b en `listar_tablero_por_articulo`. El helper MUST ser backward-safe: retorna `{}` si sin envíos → tablero igual que E1-E6. La fórmula MUST garantizar `Enviado_tablero >= 0` siempre.

**Nota Etapa 4 (2026-07-03):** Antes de Etapa 4, la columna Enviado usaba una aproximación provisional (`sum(cantidad_asignada_opt WHERE codigo_movimiento_opt > 0)`). Desde Etapa 4, la fórmula definitiva está implementada usando el ledger `MprParte/MprParteLinea/MprParteAjuste`. El tooltip "PROVISIONAL" fue eliminado del tablero.

**Nota Etapa 7 (03/07/2026):** Fórmula unificada con DOS fuentes de envío: OPT (camino legacy wizard) + tablero (camino directo componente). El término `Enviado_tablero` resta el `stock_produccion` para evitar doble conteo: cuando un envío del tablero se convierte en stock físico (vía parte OPP), el aporte del tablero baja automáticamente. Ambas fuentes son aditivas y complementarias.

#### Scenario: Sin envíos tablero — Enviado igual al OPT (backward-compat E7)

- DADO `MprEnvioProduccion` sin registros para la base_empresa
- CUANDO se calcula el tablero
- ENTONCES Enviado[comp] MUST ser igual al valor que habría dado la fórmula E1-E6 (solo Enviado_OPT)
- Y el tablero MUST funcionar sin error

#### Scenario: Con envío tablero y sin stock Producción — Enviado_tablero sube

- DADO comp_id=42 con Enviado_OPT = 10, SUM(envios_tablero) = 30, stock_produccion = 0
- CUANDO se calcula el tablero
- ENTONCES Enviado_tablero = max(0, 30 − 0) = 30
- Y Enviado[42] = 10 + 30 = 40

#### Scenario: Al registrar parte — aporte tablero baja (consumo, sin doble conteo)

- DADO comp_id=42 con SUM(envios_tablero) = 30, stock_produccion = 20
- CUANDO se calcula el tablero
- ENTONCES Enviado_tablero = max(0, 30 − 20) = 10
- Y stock_produccion NO MUST sumarse de nuevo en Enviado_OPT (sin doble conteo garantizado)

#### Scenario: Enviado_tablero nunca negativo

- DADO comp_id=42 con SUM(envios_tablero) = 10, stock_produccion = 15
- CUANDO se calcula el tablero
- ENTONCES Enviado_tablero = max(0, 10 − 15) = 0
- Y Enviado[42] = Enviado_OPT[42] + 0 >= 0

#### Scenario: Enviado derivado de OPT, no de stock Producción (preservado de E4)

- DADO OPT_liberado_acum(P) = 50, OPP_parte_acum(P) = 10, sin envíos tablero
- CUANDO se calcula el tablero
- ENTONCES Enviado_OPT = 40; Enviado_tablero = 0; Enviado[comp] = 40
- Y NO MUST derivarse de stock_deposito[Produccion]

#### Scenario: Enviado nunca negativo (preservado de E4)

- DADO OPT_liberado = 0, envios_tablero = 0
- CUANDO se calcula
- ENTONCES Enviado[comp] MUST ser 0 (no negativo)

---

### Requirement: Cálculo de Pendiente Derivado (Sin Doble Conteo)

La columna "Pendiente de producir" MUST calcularse como `max(0, Demanda_componente − [Enviado + Total])`, donde:
- `Demanda_componente` = demanda derivada de explosión BOM (pedido + reserva del pack, neteada contra stock terminado del pack)
- `Enviado` = columna virtual derivada de OPT
- `Total` = suma de columnas físicas con suma_stock='Si' (respetando el flag por depósito)

El Pendiente MUST reducirse al incrementarse Enviado o Total, evitando doble conteo.

#### Scenario: Pendiente reducido por Enviado y stock físico

- DADO un artículo A con Demanda = 100, Enviado = 30 (derivado de OPT), Total = 45 (stock físico sumable)
- CUANDO se calcula Pendiente
- ENTONCES MUST ser max(0, 100 − [30 + 45]) = 25

#### Scenario: Sin doble conteo de Enviado y Total

- DADO un artículo A con Demanda = 100, Enviado = 50, Total = 30
- CUANDO se calcula Pendiente
- ENTONCES MUST ser max(0, 100 − [50 + 30]) = 20
- Y NO MUST haber doble conteo (la fórmula resta Enviado y Total por separado, coherente con el modelo virtual/físico)

#### Scenario: Pendiente baja al enviar desde tablero (E7)

- DADO comp_id=42 con Demanda = 100, Enviado = 40, Total = 30, Pendiente = 30
- CUANDO se registra un envío de 20 unidades desde el tablero y se recalcula
- ENTONCES Enviado_tablero MUST incrementarse
- Y Pendiente MUST ser max(0, 100 − [nuevo_Enviado + 30]) < 30
- Y Pendiente MUST ser >= 0

---

### Requirement: Tablero Vivo (Refleja Stock Actual)

El tablero MUST reflejar el estado actual del stock en `stock_deposito` al momento de carga de la vista. Al realizar movimientos de stock en otra sesión o vista, el tablero SHOULD mostrar los datos actualizados al recargar la página o invocar "Actualizar demanda".

#### Scenario: Stock actualizado reflejado en recarga

- DADO un artículo A con Producción = 20 al cargar el tablero
- CUANDO en otra sesión se mueven 10 unidades de Producción a Planchado
- Y el usuario recarga el tablero
- ENTONCES la columna Producción MUST mostrar 10
- Y la columna Planchado MUST mostrar 10

---

### Requirement: Actualización de Demanda Manual

El tablero MUST proveer un botón "Actualizar demanda" que invoque el servicio `actualizar_pedidos_produccion()` (u equivalente) para recalcular la demanda desde pedidos/reserva actuales. Tras la actualización, MUST mostrarse un timestamp visible de la última actualización.

#### Scenario: Invocación de actualizar demanda recalcula

- DADO el tablero con demanda calculada hace 10 minutos
- Y se han creado nuevos pedidos desde entonces
- CUANDO el usuario hace clic en "Actualizar demanda"
- Y la operación completa exitosamente
- ENTONCES el tablero MUST reflejar la demanda actualizada (incluyendo nuevos pedidos)
- Y el timestamp de última actualización MUST actualizarse a la hora actual

---

### Requirement: Filtros por Fecha (Desde/Hasta)

El tablero MUST proveer filtros de fecha (desde/hasta) que se pasen al servicio subyacente para limitar los packs considerados en la demanda. Los filtros MUST seguir el mismo patrón UI que la vista Ventana de packs.

#### Scenario: Filtro fecha desde y hasta combinados

- DADO el tablero con filtros de fecha
- CUANDO el usuario ingresa "01/06/2026" en Desde y "30/06/2026" en Hasta
- Y aplica el filtro
- ENTONCES el sistema MUST considerar solo packs con fecha entre 01/06/2026 y 30/06/2026 inclusive

---

### Requirement: Búsqueda por Artículo (Cliente)

El tablero MUST proveer un campo de búsqueda que filtre las filas visibles por descripción de artículo en el lado cliente (Alpine.js u otro mecanismo de filtrado cliente), siguiendo el mismo patrón que la vista Tablero de KPIs.

#### Scenario: Búsqueda por descripción de artículo

- DADO el tablero renderizado con 20 artículos visibles
- Y uno de ellos es "Tela Azul 100x50"
- CUANDO el usuario escribe "Azul" en el campo de búsqueda
- ENTONCES solo las filas con artículos que contengan "Azul" en su descripción MUST permanecer visibles
- Y las demás filas MUST ocultarse (filtrado cliente)

---

### Requirement: Ordenamiento por Pendiente Descendente (Default)

El tablero MUST ordenar las filas por defecto por la columna "Pendiente de producir" en orden descendente (artículos más críticos primero). El usuario SHOULD poder cambiar el orden si la UI lo permite.

#### Scenario: Orden default por Pendiente DESC

- DADO el tablero con tres artículos: Artículo A con Pendiente = 50, Artículo B con Pendiente = 100, Artículo C con Pendiente = 20
- CUANDO se renderiza el tablero sin ordenamiento explícito del usuario
- ENTONCES las filas MUST aparecer en orden: B (100), A (50), C (20)

---

### Requirement: Acciones Consolidadas en Barra Superior (Etapa 9)

**Desde Etapa 9:** El tablero MUST exponer las acciones de transición mediante botones globales en la barra superior — "Inspección" (→ `mpr:inspeccion_lote`) y "Clasificación" (→ `mpr:clasificacion_lote`) — junto al botón "Parte de producción", con el mismo estilo (border-slate-500 bg-slate-700, icono material). El acceso a inspección y clasificación MUST realizarse exclusivamente mediante estos botones globales que llevan a pantallas de lote dedicadas (capability `mpr-acciones-lote-tablero`). La columna final por fila (renombrada "Trazabilidad") MUST conservar SOLO el enlace "Trazabilidad" condicional a `fila.id_lista_produccion`; los menús por fila "Registrar parte", "Inspección ▾" y "Transición ▾" y el modal Alpine por-fila MUST NOT renderizarse.

**Nota Histórica (Etapa 5):** El tablero incluía botones contextuales por fila con modal Alpine.js para ejecutar cada transición individualmente. **Nota Histórica (Pre-Etapa 5):** En Etapa 2, el tablero era de solo lectura sin acciones operativas por fila.

#### Scenario: Botones globales presentes (Etapa 9)

- DADO el tablero renderizado post-E9 con filas con `produccion>0` y `planchado>0`
- CUANDO se renderiza `tablero_produccion.html`
- ENTONCES aparecen botones "Inspección" y "Clasificación" en la barra superior
- Y ninguna fila muestra menús desplegables de inspección o transición

#### Scenario: Fila con OPT conserva Trazabilidad

- DADO fila con `id_lista_produccion` asignado
- CUANDO se renderiza tablero post-E9
- ENTONCES aparece enlace "Trazabilidad" para esa fila
- Y no aparecen botones "Registrar parte", "Inspección ▾", "Transición ▾"

---

### Requirement: Columna "Enviar" en Tablero (Etapa 7)

**Desde Etapa 7:** El tablero MUST incluir una columna adicional "Enviar" posicionada antes de la columna final de acciones. La columna MUST contener inputs numéricos por fila conectados a un formulario POST de lote. Los inputs MUST estar deshabilitados si `pendiente <= 0`. La columna final (columna de acciones E5; renombrada "Trazabilidad" en E9) MUST mantenerse como última columna. La demanda (urgentes, reservas, ponderación BOM) MUST calcularse igual que en E1-E6 sin cambios.

#### Scenario: Columna Enviar renderizada

- DADO el tablero renderizado post-E7
- CUANDO se inspeccionan las columnas
- ENTONCES MUST existir la columna "Enviar" antes de la columna de acciones E5
- Y la columna de acciones E5 MUST seguir siendo la última columna

#### Scenario: Reserva/urgente sin cambios (preservado)

- DADO el tablero con demanda que incluye pedidos urgentes y reservas
- CUANDO se renderiza el tablero con la columna Enviar añadida en E7
- ENTONCES la demanda de urgentes y reservas MUST calcularse igual que en E1-E6
- Y NO MUST existir cambios en la explosión BOM ni en la ponderación de reservas/urgentes

---

### Requirement: Navegación y Canon UI Synap

El tablero MUST seguir el canon UI de Synap definido en `openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md`: extends `mpr/base_mpr.html`, patrones de filtro fecha consistentes con `ventana_pack.html`, búsqueda Alpine.js consistente con `tablero.html`, sticky-left en columna Artículo. NO MUST usar como referencia visual las pantallas de Objetivos de venta ni Presupuestos (`ventas/templates/ventas/`).

#### Scenario: Enlace de acceso desde Tablero de KPIs

- DADO el usuario en la vista Tablero de KPIs (`mpr/tablero.html`)
- CUANDO inspecciona los accesos disponibles
- ENTONCES MUST existir un botón, card o enlace con etiqueta "Tablero de producción →" (o similar)
- Y al hacer clic MUST redirigir a la URL `mpr/tablero-produccion/`

---

### Requirement: Demanda Incluye Reserva de Pack (Sin Redefinición a Nivel Componente)

Al calcular la demanda de un componente, el sistema MUST considerar tanto el pedido como la reserva del pack, ambos explotados vía BOM. La reserva se mantiene a nivel PACK y NO se redefine a nivel componente individual.

#### Scenario: Demanda incluye pedido y reserva de pack

- DADO un pack P con cantidad_pedido = 10, reserva = 5, stock_terminado = 0, y BOM incluye componente A (cantidad 2 por pack)
- CUANDO se calcula la demanda de A
- ENTONCES MUST ser (10 + 5) × 2 = 30 unidades

---

### Requirement: Tablero Vacío (Sin Demanda)

Si no existen packs con demanda en el rango de fechas especificado (o sin filtros), el tablero MUST mostrar una tabla vacía o mensaje "Sin artículos con demanda" sin generar error.

#### Scenario: Sin packs con demanda

- DADO que no existen packs con demanda activa (cantidad_a_fabricar = 0 para todos)
- CUANDO se renderiza el tablero
- ENTONCES MUST mostrar una tabla vacía o mensaje informativo
- Y NO MUST generar error

---

### Requirement: Índice de Performance en stock_deposito

El sistema MUST crear un índice `idx_sd_art_dep` en la tabla `stock_deposito` de MySQL legacy sobre las columnas `(id_articulo, id_deposito)` para soportar de forma eficiente la consulta pivote del tablero consolidado. La creación del índice MUST ser idempotente (no fallar si el índice ya existe).

#### Scenario: Índice creado idempotentemente

- DADO que NO existe el índice `idx_sd_art_dep` en `stock_deposito`
- CUANDO se invoca la función que crea índices MPR (ej. `run_mpr_deposito_articulo_mysql()`)
- ENTONCES MUST crear el índice `idx_sd_art_dep ON stock_deposito(id_articulo, id_deposito)`
- Y la operación MUST completar sin error

#### Scenario: Índice ya existente no genera error

- DADO que YA existe el índice `idx_sd_art_dep` en `stock_deposito`
- CUANDO se invoca nuevamente la función que crea índices MPR
- ENTONCES NO MUST intentar crear el índice duplicado
- Y la operación MUST completar sin error (idempotencia mediante `indice_existe()` o guard equivalente)

---

## Notes

- **Ajuste Post-Verify (2026-07-02):** La columna Total fue refinada para respetar el flag `deposito.suma_stock` **por depósito individual**. Ahora `_pivot_stock_por_tipo_mpr` retorna una tupla `(stock, stock_suma)` por tipo: `stock` es el saldo real por etapa (para mostrar en las columnas), `stock_suma` es el saldo solo de depósitos con `suma_stock='Si'`. El Total se calcula como `sum(stock_suma[t] for t in TIPOS_QUE_SUMAN_STOCK)`. Se agregó el test `test_total_respeta_suma_stock_por_deposito`. Documentado en `docs/mpr/TABLERO_CONSOLIDADO.md` línea 38.

- **Fórmula Definitiva Enviado (Etapa 4, 2026-07-03):** La columna "Enviado a producción" ahora usa la fórmula definitiva `max(0, OPT_liberado_acumulado − OPP_parte_registrado_acumulado)` implementada con el ledger de partes de producción (`MprParte`, `MprParteLinea`, `MprParteAjuste`). Spec permanente: `openspec/specs/mpr-opp-parte-produccion/spec.md`. El tooltip "PROVISIONAL" fue eliminado del tablero.

- **Etapa 3 — Turnos y Roster (2026-07-03):** Implementado capability `mpr-turnos-roster` (CRUD de turnos globales + grilla semanal de planificación manual de asignación de turnos a operarios). Spec permanente: `openspec/specs/mpr-turnos-roster/spec.md`. Modelos: `MprTurno` (turnos por empresa con toggle Activo/Inactivo) y `MprRosterDia` (asignaciones roster con constraint único operario/fecha). Edición restringida a hoy/futuro; pasado solo lectura. **Insumo disponible para Etapa 4 (OPP):** los datos de `MprRosterDia` quedan listos para consumirse en la grilla OPP turno×operador×artículo (snapshot `operario_nombre` implementado en OPP para evitar dependencia en lectura de sue_abm_empleado). Documentación: `docs/mpr/TURNOS_Y_ROSTER.md`. Suite mpr: 255 tests OK, 0 regresiones.

- **Etapa 5 — Transiciones por Lote + Desmontaje (2026-07-03):** Implementado capability `mpr-transiciones-lote` (servicio `transferir_stock_entre_etapas`, modelo `MprTransicionLote`, acciones por fila en tablero). Desmontaje de `ejecutar_liberar_opt`: liberar OPT ya NO escribe stock físico en depósito Producción (solo comprobante MSTOCK virtual OPT + updates lista_produccion_agrupada). Activación de asiento físico en `registrar_parte_produccion` (OPP-parte): al registrar parte, se escribe stock físico via explosión BOM pack→componentes + flags idempotencia `movimiento_fisico_ok`/`ajuste_fisico_ok`. Columna Producción ahora se alimenta EXCLUSIVAMENTE de OPP-parte, no de OPT. Sin doble conteo: Enviado y Producción son complementarios. Spec permanente: `openspec/specs/mpr-transiciones-lote/spec.md`. Deltas en specs `mpr-opp-parte-produccion` y `mpr-pipeline-multietapa`. Suite mpr: 303 tests OK (26/26 tests etapa5), 0 regresiones. Migración 0012 aplicada. Bugs corregidos post-verify: strings template '2da Seleccion'/'Semi Elaborado' → '2daSeleccion'/'SemiElaborado'; inicialización `opt_map = {}` en `registrar_parte_produccion`.

- **Etapa 6 — Trazabilidad OPT (2026-07-03, FINAL del refactor MPR multietapa):** Implementado capability `mpr-trazabilidad-opt` (servicios `construir_trazabilidad_opt`/`construir_trazabilidad_articulo`, vista `TrazabilidadOptView`, timeline vertical). Cierre del enlace OPT↔parte: `MprParte.id_lista_produccion` (migración 0013) + escritura a `lista_produccion_historico` desde `_registrar_asiento_fisico_opp_parte`. Deprecación (solo marcada) de `ejecutar_opp`/`ejecutar_opp_por_componentes`/`RegistrarOppView`. Spec permanente: `openspec/specs/mpr-trazabilidad-opt/spec.md`. Deltas en spec `mpr-opp-parte-produccion`. Suite mpr: 322 tests PASS (19 nuevos E6, 303 previos), 0 regresiones. Verify #1019 = PASS WITH WARNINGS (warnings no bloqueantes).

- **Etapa 7 — Envío desde Tablero (03/07/2026):** Implementado capability `mpr-envio-produccion-tablero` (ledger Django `MprEnvioProduccion` desacoplado de MySQL legacy, servicio de lote atómico `enviar_a_produccion_lote`, helper backward-safe `_query_enviado_tablero_componente`, vista POST `EnviarProduccionLoteView`, UI integrada con form HTML5 `form=` attribute). Fórmula unificada de "Enviado a producción" con DOS fuentes: `Enviado = Enviado_OPT + Enviado_tablero`, donde `Enviado_tablero = max(0, SUM(envíos_tablero) − stock_produccion)` para evitar doble conteo. Migración 0014 aplicada. Spec permanente: `openspec/specs/mpr-envio-produccion-tablero/spec.md`. Deltas aplicados a esta spec (`mpr-pipeline-multietapa`). Suite mpr: 348 tests PASS (26 nuevos E7, 322 previos), 0 regresiones. Verify #1030 = PASS. El camino OPT (wizard) coexiste como camino legacy; el tablero ahora permite envío directo a nivel componente sin pasar por wizard.

- **Etapa 8 — Parte de Producción por COMPONENTE (03/07/2026):** Implementado cierre del lazo **Tablero → Fabricando (E7) → Parte por componente (E8) → Producido**. Migración del capability `mpr-opp-parte-produccion` desde nivel PACK (E4-E7) a nivel COMPONENTE conectado a `MprEnvioProduccion` (E7). Fuente de filas de la grilla del parte: query ORM `MprEnvioProduccion.filter(anulado=False)` + fórmula Fabricando (reemplaza query legacy `lista_produccion_agrupada WHERE en_proceso='Si'`). Asiento físico directo: `_registrar_asiento_fisico_opp_parte(ya_componentes=True)` escribe `stock_deposito[Producción][comp]` sin explosión BOM (parámetro `ya_componentes` backward-safe para callers legacy E5). Warning refactorizado: cantidad_registrada > Fabricando disponible (no bloqueante, en español). Keys grilla: `componentes`/`componentes_vacio` (renombrado desde `packs`/`packs_vacio`). Template: encabezado "Artículo/Componente", columna Fabricando visible. Compatibilidad E6: `MprParte.id_lista_produccion = None` (partes E8 sin traza OPT, limitación conocida). Migración 0015 aplicada (AlterField help_text `MprParteLinea.id_articulo`). Delta menor aplicado a spec `mpr-pipeline-multietapa` (esta nota). Suite mpr: 366 tests PASS (18 nuevos E8, 348 previos), 0 regresiones. Verify #1053 = PASS WITH WARNINGS (WARNING #1 template celdas resuelto post-verify por agente principal). **LAZO COMPLETO CERRADO (03/07/2026):** La columna Fabricando (E7) se reduce automáticamente cuando el parte E8 escribe `stock_produccion[comp]` sin cambio de fórmula ni doble conteo: `Fabricando[comp] = max(0, enviado_tablero − stock_prod)`. El usuario ve en el tablero "Fabricando" disponible → envía → registra parte → stock Producción sube → Fabricando baja → ciclo cerrado.

- **Refactor MPR Multietapa COMPLETADO (Etapas 1-8, 03/07/2026):** El pipeline de producción multietapa en Synap queda completo con las siguientes capabilities implementadas:
  - **E1 (Topología):** tipos MPR, depósitos físicos, configuración `tipo_mpr` por depósito, flag `suma_stock`.
  - **E2 (Tablero consolidado):** columnas canónicas Pendiente/Enviado/Producción/Planchado/2da/Semi/Scrap/Terminado/Total, explosión BOM, columna Enviado virtual con fórmula definitiva desde E4, fórmula unificada dos fuentes desde E7.
  - **E3 (Turnos y Roster):** CRUD de turnos globales, grilla semanal de planificación operario×turno.
  - **E4 (OPP-parte):** ledger de partes de producción (`MprParte/MprParteLinea/MprParteAjuste`), grilla turno×operario×pack, snapshot `operario_nombre`, activación asiento físico desde E5.
  - **E5 (Transiciones+desmontaje):** servicio `transferir_stock_entre_etapas`, modelo `MprTransicionLote`, desmontaje de `ejecutar_liberar_opt`, asiento físico en `registrar_parte_produccion`, sin doble conteo Enviado/Producción.
  - **E6 (Trazabilidad OPT):** `MprParte.id_lista_produccion`, escritura a `lista_produccion_historico`, servicios integrados de traza cronológica (6 fuentes), vista drill-down con timeline vertical.
  - **E7 (Envío desde tablero):** ledger `MprEnvioProduccion`, servicio de lote atómico `enviar_a_produccion_lote`, fórmula unificada Enviado (OPT + tablero), UI integrada con columna "Enviar" y form HTML5 `form=` attribute.
  - **E8 (Parte por componente):** Cierre del lazo Tablero→Fabricando→Parte→Producido. Grilla del parte armada desde `MprEnvioProduccion` (componentes con Fabricando>0, eliminando fuente legacy `lista_produccion_agrupada`). Registro nivel componente: `MprParteLinea.id_articulo` = ID componente. Asiento físico directo: `_registrar_asiento_fisico_opp_parte(ya_componentes=True)` sin explosión BOM. Warning vs Fabricando disponible (no bloqueante). Columna Fabricando en template, keys `componentes`/`componentes_vacio`. Compatibilidad E6: `id_lista_produccion=None` para partes E8 (sin traza OPT, limitación conocida). Lazo completo cerrado: Fabricando baja automáticamente cuando el parte E8 escribe `stock_produccion[comp]`, sin cambio de fórmula ni doble conteo.

  **Follow-ups pendientes (no bloqueantes, para iteraciones futuras):**
  - `id_lista_produccion` en `MprTransicionLote` (diferido de E6)
  - Vínculo explícito bidireccional `MprEnvioProduccion` ↔ `MprParte` (traza de consumo del envío tablero al registrar parte)
  - Comprobante MSTOCK en MySQL legacy para envíos del tablero (actualmente ledger-only Synap)
  - UI de anulación de envíos desde el tablero (actualmente solo vía admin Django)
  - Deprecación efectiva del wizard OPT como camino de envío (coexiste como camino legacy en E7)
  - Filtro temporal de ventana para `MprEnvioProduccion.creado_en` en queries (actualmente sin filtro, todos los envíos históricos suman)
  - Tests conductuales con DB real para fuentes `MprTransicionLote` y `MprArmadoSurtidoMovimiento` en `construir_trazabilidad_opt` (tests estructurales actuales OK, falta cobertura conductual)
  - Sección de componentes agrupados en la traza OPT (actualmente expandible por-evento, pendiente agrupación explícita)
  - Tests view-level de navegación desde `opt_detail` y `tablero_produccion` a trazabilidad
  - Eliminación efectiva de `ejecutar_opp`/`ejecutar_opp_por_componentes`/`RegistrarOppView` + reescritura wizard paso 3 (requiere migración wizard a patrón OPP-parte)
  - WebSockets/auto-refresh en tablero consolidado (fuera de alcance E1-7)

- **Etapa 9 — Acciones Consolidadas del Tablero (03/07/2026):** Implementado capability `mpr-acciones-lote-tablero` (pantallas de lote Inspección y Clasificación + servicio batch `transferir_stock_lote`). Las acciones por fila de E5 ("Registrar parte", "Inspección ▾", "Transición ▾" + modal Alpine) fueron eliminadas del tablero y reemplazadas por botones globales en la barra superior ("Inspección" → `mpr:inspeccion_lote`, "Clasificación" → `mpr:clasificacion_lote`) que llevan a pantallas multilínea con template compartido `transicion_lote_masiva.html`. Cada pantalla reparte cada componente entre dos destinos (Inspección: Planchado/Desperdicio; Clasificación: 2da Selección/Semi Elaborado) con **bloqueo por tope de stock físico** re-validado server-side (no confía en el hidden `disponible_{id}`). `transferir_stock_lote` es best-effort (sin `atomic()`) y reutiliza `transferir_stock_entre_etapas` sin modificarlo; `TransicionLoteView`/`mpr:transicion_lote` se conservan backward-safe. La columna final por fila se renombró "Trazabilidad" y conserva solo el enlace de traza. Spec permanente: `openspec/specs/mpr-acciones-lote-tablero/spec.md`. Deltas en `mpr-transiciones-lote` y esta spec. Sin migración de esquema. Suite mpr: 397 tests PASS (31 nuevos E9, 366 previos), 0 regresiones (26/26 etapa5). Verify #1068 = PASS WITH WARNINGS (W-1 aislación base_empresa y W-2 botones globales cerrados post-verify con tests adicionales).

- **Fuera de Alcance Etapa 2:** ✅ Transiciones por lote (implementado en Etapa 5). Pendiente: WebSockets/auto-refresh.
