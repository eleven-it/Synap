# Spec: Pedido simple unificado (masivo 1 sucursal)

**Capability:** `ecom-pedido-simple-unificado`  
**Change:** `ecom-pedido-simple-unificado-masivo`  
**Ruta canónica:** `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple`

## Purpose

Unificar «Pedido simple» como variante de pedido masivo con una sola columna (domicilio operativo), borrador `EcomPedidoMasivoDraft`, carga/edición/consulta de PED vía `?cod_mov=` y paridad funcional con el antiguo OrderShell (mail, crédito, repetir, PDF, anular).

## Requirements

### REQ-PSU-01 — Ruta canónica y parámetros

El sistema MUST servir pedido simple en `/ecom/mayoristapp/pedido-masivo-sucursales/` con `?modo=simple`. MUST aceptar `draft`, `cod_mov` e `id_domicilio` en query según el caso. MUST NOT usar `/ecom/mayoristapp/venta/` como pantalla activa de captura.

#### Scenario: Nuevo pedido simple

- **GIVEN** usuario con permiso de pedido simple o masivo
- **WHEN** abre `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple`
- **THEN** MUST mostrar UI «Pedido simple» con matriz de una columna editable

#### Scenario: Continuar borrador

- **GIVEN** borrador masivo activo del usuario
- **WHEN** abre con `?modo=simple&draft={id}`
- **THEN** MUST restaurar celdas y contexto comercial del borrador

---

### REQ-PSU-02 — Matriz de una columna

En `modo=simple`, la pantalla MUST mostrar exactamente una columna de sucursal (`id_domicilio_fijo` del draft o domicilio del PED). MUST usar etiqueta «Pedido simple» en título y CTAs. MUST ocultar columnas adicionales aunque el cliente tenga más domicilios activos.

#### Scenario: Cliente multi-sucursal en modo simple

- **GIVEN** cliente con 3 domicilios activos y domicilio operativo D1 seleccionado
- **WHEN** captura en `modo=simple`
- **THEN** MUST ver 1 columna para D1
- **AND** MUST NOT mostrar columnas de los otros domicilios

---

### REQ-PSU-03 — Borrador con metadata de origen

`EcomPedidoMasivoDraft` en pedido simple MUST persistir `cod_mov_origen` (nullable) e `id_domicilio_fijo` (obligatorio tras elegir cliente o cargar PED). El autoguardado MUST mantener celdas en `EcomPedidoMasivoDraftCelda` con la misma semántica de packs que masivo multi-sucursal.

#### Scenario: Draft nuevo con domicilio fijo

- **GIVEN** usuario elige cliente y domicilio D1 en pedido simple
- **WHEN** agrega la primera cantidad
- **THEN** el draft MUST tener `id_domicilio_fijo=D1` y `cod_mov_origen` null

#### Scenario: Draft desde PED pendiente

- **GIVEN** PED pendiente no anulado con domicilio D2
- **WHEN** abre `?modo=simple&cod_mov={id}`
- **THEN** el draft MUST tener `cod_mov_origen={id}` e `id_domicilio_fijo=D2`

---

### REQ-PSU-04 — Carga de PED existente en draft

Al abrir `?cod_mov=` en pedido simple, el sistema MUST validar el PED como plantilla (`validar_pedido_como_plantilla`), MUST copiar renglones `stockp` a celdas del draft (servicio `cargar_pedido_en_draft_masivo`) y MUST NOT mutar MySQL hasta confirmar. Solo MUST aceptar `TipoComprobante='PED'`.

#### Scenario: PED pendiente editable

- **GIVEN** PED Pendiente no anulado
- **WHEN** abre en pedido simple con `cod_mov`
- **THEN** MUST hidratar celdas con cantidades convertidas a packs Bulto>Display
- **AND** MUST permitir editar cantidades en la matriz

#### Scenario: PED anulado o inexistente

- **GIVEN** `cod_mov` anulado o inválido
- **WHEN** intenta abrir en pedido simple
- **THEN** MUST mostrar error en español
- **AND** MUST NOT crear draft editable con datos del PED

#### Scenario: Conversión packs con redondeo

- **GIVEN** renglón con UOM no estándar respecto a Bulto/Display
- **WHEN** carga el PED en draft
- **THEN** MUST aplicar conversión documentada
- **AND** SHOULD informar al usuario si hubo redondeo en alguna línea

---

### REQ-PSU-05 — Modo según estado del PED

Si el PED origen tiene `Estado='Pendiente'` y `Anulado≠Si`, pedido simple MUST permitir editar celdas y confirmar. Si el PED está en producción o anulado, MUST ser solo lectura (sin confirmar ni mutar cantidades).

#### Scenario: Consulta PED en preparación

- **GIVEN** PED con `Estado='En preparación'`
- **WHEN** abre `?modo=simple&cod_mov=`
- **THEN** MUST mostrar matriz read-only
- **AND** MUST NOT mostrar CTA confirmar cambios

---

### REQ-PSU-06 — Confirmación anula+crea (paridad REQ-VTA-04)

Al confirmar edición de un PED Pendiente cargado en draft, el sistema MUST exigir modal Synap de riesgos, MUST anular el `cod_mov_origen` y MUST crear un nuevo PED vía `mayorista_checkout_service.confirmar` (no UPDATE in-place). Para pedido nuevo sin origen, MUST confirmar un único PED de la columna.

#### Scenario: Confirmar edición pendiente

- **GIVEN** draft con `cod_mov_origen` y cambios en celdas
- **WHEN** confirma tras modal Synap
- **THEN** MUST anular el PED origen
- **AND** MUST crear un nuevo PED con número distinto
- **AND** MUST marcar el draft como confirmado o archivado según política masiva

#### Scenario: PED origen anulado externamente

- **GIVEN** draft con `cod_mov_origen` ya anulado en AdministraNET
- **WHEN** intenta confirmar
- **THEN** MUST fallar con mensaje en español
- **AND** MUST dejar el draft en BORRADOR editable

---

### REQ-PSU-07 — Acciones hero (mail, crédito, repetir, PDF, anular)

Con un PED cargado o tras confirmación, pedido simple MUST ofrecer según corresponda: widget crédito del cliente, Enviar mail, Repetir pedido, Ver PDF y Anular (solo si `puede_anular`). MUST reutilizar APIs existentes del ecosistema mayorista.

#### Scenario: Mail manual en consulta

- **GIVEN** PED consultado con cliente con email
- **WHEN** pulsa Enviar mail
- **THEN** MUST encolar envío vía `mail_enqueue` o equivalente existente

#### Scenario: Repetir pedido

- **GIVEN** PED válido como plantilla
- **WHEN** pulsa Repetir pedido
- **THEN** MUST crear nuevo draft simple con celdas copiadas (no `EcomCart` borrador)

#### Scenario: Anular solo si permitido

- **GIVEN** cabecera con `puede_anular=true`
- **WHEN** muestra barra de acciones
- **THEN** MUST mostrar acción Anular

---

### REQ-PSU-08 — Solo PED, packs Bulto>Display, catálogo sin filtro stock

Pedido simple MUST operar exclusivamente con `TipoComprobante='PED'`. MUST NOT ofrecer PRE ni DEV. Las cantidades MUST expresarse en packs con jerarquía fija Bulto>Display. El buscador de artículos MUST NOT filtrar por stock disponible en captura; la validación de stock en commit MAY seguir `ecom_validar_stock_pedidos`.

#### Scenario: Catálogo sin filtro stock

- **GIVEN** artículo sin stock disponible
- **WHEN** busca y agrega en pedido simple
- **THEN** MUST permitir agregarlo a la matriz
- **AND** MAY rechazar en confirmación si la config exige validación de stock

---

### REQ-PSU-09 — Permisos unificados

El acceso a pedido simple MUST estar permitido a usuarios con `ecom.pedido_masivo.usar` o permiso equivalente unificado de pedidos de venta. MUST NOT bloquear usuarios que antes capturaban en `/venta/` sin el permiso masivo, salvo decisión explícita de producto documentada en diseño.

#### Scenario: Usuario legacy de pedido simple

- **GIVEN** usuario con permiso histórico de pedidos sin `ecom.pedido_masivo.usar`
- **WHEN** intenta abrir pedido simple
- **THEN** MUST poder acceder tras unificación de permisos definida en diseño

---

### REQ-PSU-10 — Redirect legacy desde venta

`/ecom/mayoristapp/venta/` y `/ecom/mayoristapp/compra/` MUST responder 302 hacia pedido masivo `?modo=simple`, preservando query (`cod_mov`, `draft` si aplica). Bookmarks y deep links PWA MUST seguir funcionando vía redirect.

#### Scenario: Bookmark /venta/

- **GIVEN** usuario con URL guardada `/ecom/mayoristapp/venta/?cod_mov=12345`
- **WHEN** navega a esa URL
- **THEN** MUST recibir 302 a `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple&cod_mov=12345`
