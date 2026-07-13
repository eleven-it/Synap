# Checklist de regresión — Rediseño UI de pedidos

**Proyecto:** Synap · `ecom` mayoristapp  
**Fecha de referencia:** 10/07/2026  
**Uso:** ejecutar manualmente en staging (y spot-check en producción post-deploy). Marcar `[x]` al validar.

**Leyenda verificación F5**

| Marca | Significado |
|-------|-------------|
| `[x]` + *(código)* | Verificado por inspección de templates/JS (F1–F5) |
| `[x]` + *(tests)* | Cubierto por suite automatizada §21 |
| `[ ]` + *(MANUAL)* | Requiere QA humano en browser/staging |

**Pre-requisitos**

- Contenedor Synap activo: `docker exec Synap_app ...`
- Usuario **vendedor** con permisos `ecom.carrito.editar`, `ecom.pedidos.crear`, `ecom.pedidos.ver`
- Usuario **cliente** autogestión ( `tipousuario = cliente` )
- Cliente de prueba con crédito conocido, lista de precios y artículos con/sin stock
- Tests automatizados en verde (ver sección final)

---

## 1. Creación de comprobantes

### 1.1 Pedido (PED)

- [ ] Vendedor: hub → Nuevo pedido → `/ecom/mayoristapp/compra/` carga sin error *(MANUAL)*
- [ ] GET compra limpia cliente previo y carrito borrador (vendedor) *(MANUAL — regla backend)*
- [ ] Seleccionar cliente habilita catálogo y pedidos recientes *(MANUAL)*
- [ ] Agregar ≥2 artículos distintos al carrito *(MANUAL)*
- [x] Totales (subtotal, IVA, total) coinciden con respuesta API `GET carrito/` *(código: `setCart` + binding `tot`; tests: `test_mayorista_cart_service`)*
- [ ] Confirmar PED → mensaje éxito con número y link a detalle `/ecom/mayoristapp/pedidos/<cod_mov>/` *(MANUAL)*
- [ ] Pedido aparece en listado `/ecom/mayoristapp/pedidos-vendedor/` *(MANUAL)*
- [ ] Estado inicial coherente (Pendiente / según backend) *(MANUAL)*

### 1.2 Presupuesto (PRE)

- [x] Toggle PRE en compra cambia estilo shell (amber) y tipo en carrito (`PATCH tipo-comprobante`) *(código: `solicitarCambiarTipo`, tokens PRE; tests: render compra)*
- [ ] Confirmar PRE → éxito con link detalle `/ecom/mayoristapp/comprobantes/<cod_mov>/` *(MANUAL)*
- [ ] PRE listado en `/ecom/mayoristapp/presupuestos-vendedor/` *(MANUAL)*

### 1.3 Devolución (DEV)

- [x] Toggle DEV cambia estilo shell (rose) *(código: tokens DEV + `modoShellClass`)*
- [x] Agregar artículo sin validación de stock bloqueante *(tests: `test_mayorista_cart_service` modo DEV)*
- [ ] Confirmar DEV → detalle comprobante accesible *(MANUAL)*

---

## 2. Edición de carrito (borrador)

- [ ] Aumentar/disminuir cantidad vía UI actualiza línea y totales (solo backend) *(MANUAL)*
- [ ] Eliminar una línea vía DELETE ítem *(MANUAL)*
- [x] Vaciar carrito con confirmación *(código: `solicitarVaciar()` + modal canon; sin `confirm()` nativo en compra)*
- [ ] Cambiar cliente (vendedor) vacía carrito y muestra aviso *(MANUAL)*
- [ ] Recargar página mantiene borrador `EcomCart` (mismo cliente) *(MANUAL)*
- [x] Carrito vacío muestra estado empty correcto *(código: empty «No hay líneas en el pedido»)*

## 3. Guardado borrador

- [ ] Salir de compra y volver: líneas persisten (mismo usuario/cliente) *(MANUAL)*
- [ ] Vendedor nueva visita GET compra: borrador reiniciado *(MANUAL — regla backend)*
- [ ] Cliente autogestión: borrador persiste entre sesiones cortas (misma sesión Django) *(MANUAL)*

## 4. Confirmación y post-checkout

- [x] Botón confirmar deshabilitado durante POST *(código: `confirmando` + `:disabled` en modal resumen)*
- [ ] Doble clic no duplica pedido (idempotencia backend) *(MANUAL)*
- [ ] Panel éxito: «Nuevo comprobante» limpia UI *(MANUAL)*
- [ ] Link «Ir al hub» funciona *(MANUAL)*
- [ ] Observaciones enviadas aparecen en detalle (si backend las persiste) *(MANUAL)*
- [ ] Fecha entrega texto se guarda cuando se completa *(MANUAL)*

## 5. Cálculos, precios e impuestos

- [x] Precio unitario mostrado = `serializar_carrito` (no editar en UI) *(código: binding RO en líneas)*
- [x] Cambio cantidad recalcula vía servidor, no JS local *(código: PATCH + `setCart`; tests: cart service)*
- [ ] Descuento pie aplicado refleja totales actualizados *(MANUAL)*
- [ ] IVA y percepciones (si aplican cliente/sucursal) coherentes con detalle *(MANUAL)*
- [ ] Promoción activa modifica precio según reglas backend *(MANUAL)*
- [x] Formato moneda consistente (separador miles, decimales) *(código: `money()` Intl es-AR)*

## 6. Descuentos

- [ ] Descuento pie: valor válido aceptado *(MANUAL)*
- [x] Descuento pie: valor inválido muestra error sin corromper carrito *(código: `descPieError` inline + flash)*
- [x] Descuento renglón: sin UI — verificar que flujo no expone control accidental *(código: no hay control renglón en templates)*

## 7. Stock

- [ ] PED: artículo sin stock → mensaje error 409 o warning según regla *(MANUAL)*
- [ ] PRE: misma validación que PED *(MANUAL)*
- [x] DEV: permite cantidades sin chequeo stock disponible *(tests: cart service DEV)*
- [ ] Stock disponible visible en grilla catálogo (si aplica) *(MANUAL)*
- [x] Stock comprometido **no** requerido en UI (gap conocido) *(código: sin control en UI)*

## 8. Cliente

- [ ] Búsqueda autocomplete ≥2 caracteres *(MANUAL)*
- [ ] Selección fija cliente en sesión *(MANUAL)*
- [ ] Widget crédito: saldo, límite días, autorizado / no autorizado *(MANUAL)*
- [x] Cliente sin autorización: pedido se registra con aviso (regla negocio) *(código: aviso crédito informativo; no bloquea)*
- [x] Alta rápida cliente **no** disponible en UI (gap conocido) *(código)*
- [ ] Autogestión: panel cliente oculto; catálogo con lista propia *(MANUAL)*

## 9. Entrega y datos logísticos

- [ ] Campo texto entrega acepta entrada y se envía en checkout *(MANUAL)*
- [x] Dirección entrega: selector **no** presente (API existe — gap conocido) *(código)*
- [x] Transporte / sucursal / depósito: sin controles UI (gaps conocidos) *(código)*

## 10. Errores y estados UI

- [x] Sin cliente: no permite agregar artículos / confirmar (mensaje claro) *(código: `intentoSinCliente`, gate en `agregar`)*
- [x] Error red: flash error sin pantalla en blanco *(código: `flash()` + aria-live)*
- [x] Loading grilla catálogo visible durante búsqueda *(código: estado loading catálogo)*
- [x] Empty catálogo: mensaje cuando sin resultados *(código)*
- [ ] Error stock: mensaje comprensible en español *(MANUAL)*
- [ ] Sesión expirada redirige a login sin JSON crudo *(MANUAL)*

---

## 11. Permisos — vendedor vs cliente

### 11.1 Vendedor

- [ ] Acceso hub, compra, listado, detalle *(MANUAL)*
- [x] Panel búsqueda cliente visible *(código: header sticky compra)*
- [ ] Filtro vendedor en listado operativo *(MANUAL)*
- [ ] Sin permiso `ecom.pedidos.crear`: bloqueo coherente en compra/checkout *(MANUAL)*

### 11.2 Cliente autogestión

- [ ] Acceso `/ecom/mayoristapp/compra/` con su cliente *(MANUAL)*
- [ ] No ve listado gerencial completo (según permisos) *(MANUAL)*
- [ ] GET compra **no** limpia su carrito al entrar *(MANUAL — tests: `test_compra_mayorista_cliente`)*
- [ ] Precios/totales según su lista *(MANUAL)*

---

## 12. Responsive

- [x] Desktop ≥1280px: layout catálogo + resumen lateral *(código: grid `lg` 2fr/1fr + summary sticky)*
- [ ] Tablet 768–1024px: sin solapamiento crítico *(MANUAL)*
- [ ] Móvil 375px: agregar ítem, ver total, bottom bar, confirmar *(MANUAL)*
- [ ] Tabla listado pedidos: scroll horizontal usable *(MANUAL)*
- [ ] Hub KPIs legibles en móvil *(MANUAL)*
- [x] Botones CTA ≥44px alto en touch *(código: stepper/min-h 2.75rem en qty y CTA summary)*

---

## 13. Teclado y accesibilidad

- [x] Búsqueda artículos: ↑ ↓ mueven selección *(código: `compra_mayorista_catalogo.mjs`)*
- [x] Enter agrega artículo seleccionado *(código)*
- [ ] Tab order lógico en formulario cliente y búsqueda *(MANUAL)*
- [x] Foco visible en controles interactivos *(código: tokens `:focus-visible`)*
- [x] `aria-live` o equivalente para mensajes flash *(código: `#pedidos-aria-live` + `announceAriaLive`)*
- [x] Toggle PED/PRE/DEV accesible por teclado *(código: `role=tablist`, `solicitarCambiarTipo`)*
- [x] Modal repetir pedido: Escape cierra (si implementado F3/F4) *(código: `order_dialogs` Esc; repetir modal data-repetir-cerrar)*

---

## 14. Compatibilidad backend (sin cambios)

- [x] Payload POST `carrito/` sin campos nuevos inventados *(tests + sin diff backend)*
- [x] PATCH ítem solo campos soportados por relay *(código: cantidad/UOM existentes)*
- [x] POST `checkout/confirmar/` body sin alteración de contrato *(código: `compra_mayorista_checkout.mjs`)*
- [x] Respuestas usan `serializar_carrito` — UI no espera campos inexistentes *(código: `setCart`)*
- [x] `ajax=1` no requerido en flujo compra *(código)*
- [x] API v1 listado pedidos sigue funcionando para `pedidos_vendedor.js` *(tests: `test_api_v1_pedidos`)*

---

## 15. Repetir pedido

- [x] Chips pedidos recientes visibles con cliente seleccionado *(código: banner recientes compra)*
- [ ] Clic chip → preview modal con totales/líneas *(MANUAL)*
- [ ] Confirmar carga en carrito vía `POST carrito/desde-pedido/` *(MANUAL)*
- [ ] Modal repetir desde listado/detalle (`repetir_pedido_modal.js`) *(MANUAL)*
- [ ] Carrito previo: confirmación antes de sobrescribir *(MANUAL)*

---

## 16. Anular pedido

- [ ] Anulación desde UI listado/detalle (si expuesta) llama relay `comprobantes/anular-pedido/` *(MANUAL — detalle usa `confirm()` nativo, fuera scope compra)*
- [ ] Pedido anulado aparece marcado en listado (rojo / Anulado=Si) *(MANUAL)*
- [x] Pedido anulado no editable desde compra *(código: política anular+repetir; sin edición confirmados)*

---

## 17. PDF

- [ ] Generar/descargar PDF desde detalle PED (`/ecom/api/mayoristapp/comprobantes/pedidos/<cod_mov>/pdf/`) *(MANUAL)*
- [ ] PDF abre o descarga sin error 500 *(MANUAL)*
- [ ] Datos PDF coherentes con detalle pantalla *(MANUAL)*

---

## 18. Mail

- [ ] Envío mail comprobante (si botón visible en detalle) encola correctamente *(MANUAL)*
- [ ] Estado cola mail consultable sin error *(MANUAL)*
- [ ] Mensaje éxito/error en español *(MANUAL)*

---

## 19. Convertir presupuesto (PRE → PED)

- [ ] Desde detalle PRE: acción convertir disponible según permisos *(MANUAL)*
- [ ] `POST presupuestos/<cod_mov>/convertir-pedido/` crea PED *(MANUAL)*
- [ ] Nuevo PED visible en listado y detalle *(MANUAL)*
- [ ] PRE origen mantiene estado esperado (no duplicado incorrecto) *(MANUAL)*

---

## 20. Listados y detalle (no compra)

- [ ] Hub KPIs cargan (`pedidos/kpis` o contexto servidor) *(MANUAL)*
- [ ] Listado filtros: vendedor, fechas, estado, búsqueda número *(MANUAL)*
- [ ] Export CSV listado funciona *(MANUAL)*
- [ ] Detalle PED: cabecera, líneas, totales, acciones hero *(MANUAL)*
- [ ] Detalle PRE/DEV: ruta comprobantes correcta *(MANUAL)*
- [x] Breadcrumb y navegación hub ↔ listado ↔ detalle *(código: `pedidos_breadcrumb.html` en pantallas)*
- [x] Fechas listado en formato `dd/MM/yyyy` *(código: relay `FechaB` DATE_FORMAT; sin ISO en UI listado)*

---

## 21. Regresión automatizada (obligatoria pre-merge)

Ejecutar y verificar **OK**:

```bash
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_view
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_cliente
docker exec Synap_app python manage.py test ecom.tests.test_mayorista_cart_service
docker exec Synap_app python manage.py test ecom.tests.test_pedido_gestion
docker exec Synap_app python manage.py test ecom.tests.test_pedidos_vendedor
docker exec Synap_app python manage.py test ecom.tests.test_api_v1_pedidos
```

- [x] Todos los tests anteriores pasan *(tests: checkpoint F5)*
- [x] Sin nuevos errores linter en templates/JS tocados *(código: sin cambios backend)*

---

## 22. Registro de ejecución

| Campo | Valor |
|-------|-------|
| Ejecutor | |
| Fecha | __/__/2026 |
| Ambiente | staging / producción |
| Build / commit | |
| Navegadores | Chrome / Firefox / Safari / Edge |
| Viewports probados | 375 / 768 / 1280 |
| Resultado global | PASS / FAIL |
| Incidencias | |

### Incidencias (plantilla)

| ID | Sección | Descripción | Severidad | Ticket |
|----|---------|-------------|-----------|--------|
| | | | bloqueante / mayor / menor | |

---

## 23. Criterio de release

**PASS** si:

- Todos los ítems **críticos** (§1, §2, §4, §5, §7, §11, §14, §21) marcados
- Cero incidencias **bloqueantes** abiertas
- Tests automatizados en verde

**FAIL** si cualquier flujo PED confirmación o integridad totales falla.

---

*Última actualización: 10/07/2026 · Verificación F5: 38 ítems *(código/tests)*, resto *(MANUAL)*.*
