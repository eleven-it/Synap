# Ventas Objetivos vs BO - Filtros incluir, orden y performance

Fecha: 30/04/2026

## Alcance

Se actualiza el reporte `ventas-objetivos-vs-bo` con:

- Filtros nuevos `clientes_incluir` y `vendedores_incluir`.
- Reorganización visual de filtros:
  - `Sucursal | Lista de precios`
  - `Clientes a incluir | Clientes a excluir`
  - `Vendedores a incluir | Vendedores a excluir`
  - `Depósitos`
  - Un único bloque DOM para «Vendedores a excluir» (`#vendedores_excluidos`), compartido con el partial de filtros BO/PV/sucursales (sin segundo include que duplicara `id`). El texto de ayuda bajo ese campo solo se muestra cuando `report.slug == 'ventas-objetivos-vs-bo'`.
  - Los controles `Ordenar por` y `En forma` se muestran en la toolbar de la tabla jerárquica, a continuación de `Expandir todo`, `Contraer todo` y el buscador (etiquetas en línea con cada `<select>` para no aumentar la altura de la barra).
- Nuevos filtros de orden:
  - `ordenar_por`: `objetivo_meta`, `objetivo_falta`, `total_ventas_periodo`
  - `orden_forma`: `asc`, `desc`
- Jerarquía de presentación:
  - `Vendedor`
    - `Con compra`
    - `Sin compra`
    - luego `Cliente -> Rubro -> Subrubro -> Artículo`
  - En rubro/subrubro/artículo la UI muestra **unidades**, **facturación** y BO agregado; **remitos**, **pedidos en armado** y **total** consolidado quedan en **—** (solo hay datos de cabecera `comp_ped` en el renglón cliente). **Objetivo** y **falta** siguen solo en cliente/vendedor.
- Contadores:
  - Vendedor con total de clientes.
  - Nodo `Con compra`/`Sin compra` con cantidad de clientes.
- Refactor de encabezado:
  - Grupo `OBJETIVO` con subcolumnas `META` y `FALTA`.
  - **FALTA (solo visualización en web):** se muestra como `−(objetivo − facturación − remitos)` del backend: valor **negativo** si aún no se cumplió el objetivo, **positivo** si ya se superó; el cálculo y totales del informe no cambian.

## Reglas funcionales

- Reconciliación de incluir/excluir por interacción:
  - Si un ID se selecciona en incluir, se elimina de excluir.
  - Si un ID se selecciona en excluir, se elimina de incluir.
- En la UI del componente de tags (`initializeTagsFilter` en `reports/static/reports/js/dashboard.js`), los desplegables de búsqueda **no muestran** los IDs que ya están seleccionados en el campo opuesto (pares `clientes_incluir` ↔ `clientes_excluidos` y `vendedores_incluir` ↔ `vendedores_excluidos` solo en `ventas-objetivos-vs-bo`). Si el usuario cambia la selección en el peer, la lista abierta se refresca para aplicar el filtro.
- Ordenamiento:
  - Aplica a todos los niveles.
  - En empate de métrica, desempate alfabético.
  - Cambio de `ordenar_por` o `orden_forma` en la UI dispara recarga inmediata del dashboard (sin esperar otro control).

## Instrumentación de performance

Se agrega medición por fases del runner y registro en `ReportExecutionLog`.

**Visibilidad:** los datos de performance (timings en `meta.filters_applied` y el detalle en `ReportExecutionLog` vía admin de Django) solo los ve el usuario administraNET con **`cod_usuario` igual a `supervisor`** (minúsculas). No aplica al puesto ni rol «Supervisor» ni a otros usuarios, aunque tengan permisos de reportes o sean superuser en Django sin ese `cod_usuario`.

Campos relevantes:

- Filtros aplicados (incluyendo períodos y listas de incluir/excluir).
- Configuración de orden (`ordenar_por`, `orden_forma`).
- `performance.phase_ms` por fase.
- `performance.duration_total_ms`.
- Contexto de ejecución (`timestamp`, `report_slug`, `username`).

Retención:

- Se conservan solo las últimas 10 ejecuciones por `reporte + usuario`.

