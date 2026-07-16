# Spec: Hub Pedidos Lista | Kanban

**Capability:** `ecom-pedidos-hub-kanban`  
**Origen:** changes `ecom-pedidos-hub-kanban-masivo-sucursales` (13/07/2026), `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026)  
**Ruta:** `/ecom/mayoristapp/pedidos/`

## Requirements

### REQ-HUB-01 — Home operativa
El sistema MUST servir `/ecom/mayoristapp/pedidos/` como pantalla inicial de Pedidos con vistas **Lista** y **Kanban** (toggle). MUST usar canon visual Tablero de producción (header slate, viewport flex).

#### Scenario: Entrada al módulo
- **GIVEN** un usuario con permiso de ver pedidos
- **WHEN** navega a `/ecom/mayoristapp/pedidos/`
- **THEN** MUST ver el tablero Lista|Kanban (no el hub solo-KPI legacy)

### REQ-HUB-02 — Columnas de estado
El Kanban/Lista MUST incluir al menos: Borrador, Enviado, Por autorizar, Aprobado, Anulado. Borrador MUST incluir carritos `EcomCart` con ítems y borradores de pedido masivo del usuario.

#### Scenario: Borrador visible
- **GIVEN** un borrador masivo en estado BORRADOR del usuario
- **WHEN** abre el hub
- **THEN** MUST aparecer en Borrador con CTA Continuar

### REQ-HUB-03 — Recuperación
Al continuar un borrador, el sistema MUST abrir la pantalla de edición correspondiente (compra simple o matriz masiva) con los datos persistidos. Si el usuario elige Nuevo con borrador activo, MUST pedir confirmación Continuar vs Archivar y crear.

#### Scenario: Nuevo con borrador existente
- **GIVEN** borrador activo
- **WHEN** elige Nuevo → Masivo
- **THEN** MUST mostrar modal de decisión y MUST NOT pisar el borrador sin confirmación

### REQ-HUB-04 — Acciones
Desde una tarjeta/fila de PED confirmado, el usuario MUST poder abrir el detalle. El sistema SHOULD ofrecer Autorizar solo con permiso. Fechas en UI MUST ser `dd/MM/yyyy`.

### REQ-HUB-05 — Alcance comercial

El hub MUST filtrar vía `alcance_viajantes_comercial`. Con workflow OFF MUST aplicar filtros actuales (JSON/`ecom.pedidos.ver_todos`). Con aprobación ON MUST exponer cola comercial (`por_aprobar`).

#### Scenario: Supervisor con workflow ON

- **GIVEN** master ON y usuario supervisor con subárbol org
- **WHEN** abre el hub
- **THEN** MUST ver solo pedidos del subárbol org

---

### REQ-HUB-06 — Vista mobile

En viewports `<lg` MUST mostrar chips+cards sin scroll horizontal, manteniendo REQ-HUB-01–04 (columnas, borradores, recuperación).

#### Scenario: Borrador en móvil

- **GIVEN** borrador activo en viewport móvil Nivel A
- **WHEN** el usuario continúa
- **THEN** MUST abrir edición (REQ-HUB-03)
