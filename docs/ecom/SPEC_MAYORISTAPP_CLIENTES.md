# Spec — Clientes y domicilios (mayoristapp)

**Relays:** `relay-cliente-domicilio.php`, `relay-cliente-rapido.php`, `relay-clientes.php`, `relay-contacto-cliente.php`; parcialmente relacionado `relay-tipo-cliente.php` (subrubros → [SPEC_CATALOGO_RUBRO.md](./SPEC_CATALOGO_RUBRO.md) §4).  
**Checkpoint sugerido:** `mayoristapp_clientes`.

---

## 1 — Alcance funcional (desde PHP)

- Búsqueda y alta/edición de clientes según permisos `todos_clientes` / `CodViajante`.
- Domicilios múltiples por cliente.
- Contactos asociados.
- Filtros por vendedor y listas rápidas para carrito/pedidos.

---

## 2 — Synap objetivo

- Servicios en `ecom/` o reutilización de consultas existentes en otras apps si ya hay API interna de clientes.
- SQL **parametrizado**; tipos AdministraNET vía `core.utils.administranet_types` en escrituras.
- Permiso: `EcomMayoristappSessionPermission` + reglas de negocio (solo mis clientes) en servicio.

---

## 3 — Contratos API (Fase C v1 — `relay-clientes.php`)

| Acción PHP | Método | Ruta Synap | Notas |
|------------|--------|------------|--------|
| `buscarCliente` (POST) | POST | `/ecom/api/mayoristapp/clientes/buscar/` | Cuerpo JSON: `buscarCliente=1`, `queCliente`, `claseBusqueda` (`codigo` \| `texto`), `codigo`. O GET `?ajax=1&modoBus=&patron=&codigo=&limit=`. Respuesta: `{ "clientes": [...], "total" }`. Sesión: `user.todos_clientes`, `usa_id_manual`, `supervisor_venta` / `permiso_supervisor_venta_web`, `vendedor_a_cargo`, `id_vendedor_usr`. |
| `traeDatosClienteSeleccionado` | GET | `/ecom/api/mayoristapp/clientes/seleccionado/?ajax=1` | JSON: datos en `mayoristapp.cliente` o `session.cliente`. |
| `seleccionarComprobante` | GET | `/ecom/api/mayoristapp/clientes/comprobante-formulario/?ajax=1&frm=0..5` | Respuesta `{ "estado":"ok", "url", "formulario" }`; guarda en `mayoristapp.formulario` / `u_formulario`. |
| `selecciona_cliente` | POST | `/ecom/api/mayoristapp/clientes/seleccionar/?ajax=1` | Cuerpo JSON `codigo` o `codCliente`. Persiste en `mayoristapp` + raíz de sesión: `cliente` (lista `[datos, autoriza_credito]`), `idcliente`, `domicilios_cliente`, `iva_incluido` / `ivaIncluido`; vacía `jcart`. |
| Domicilio (GET) | GET | `/ecom/api/mayoristapp/clientes/domicilio/?ajax=1&accion=…` | `accion=traer&idDomicilio=` devuelve `{ dom, prov, dep, dist, zona }`. `provincia` \| `departamento` \| `distrito` \| `zona` con filtros `idPais`, `idProvincia`, `idDepartamento` según PHP. |
| Domicilio (POST) | POST | `/ecom/api/mayoristapp/clientes/domicilio/?ajax=1` | `accion=alta` \| `editar`; mismos nombres de campos que `relay-cliente-domicilio.php` (`calleCliente`, `idCliente`, `idClienteDom`, sufijos `Ed`, etc.). |
| Opciones visita | GET | `/ecom/api/mayoristapp/clientes/domicilio-opciones-visita/?traeVisita=1&tipoVisita=` | Paridad `trae_opciones_visita`. |
| Contacto | GET | `/ecom/api/mayoristapp/clientes/contacto/?ajax=1&accion=lista` | Requiere `idcliente` en sesión. Respuesta JSON `{ contactos, total }` (PHP devolvía HTML `<option>`). |
| Contacto | POST | `/ecom/api/mayoristapp/clientes/contacto/?ajax=1` | `accion=alta` + campos `nombreContacto`, `tipoDocContacto`, `nroDocContacto`, etc.; `contacto_completo` en `session.user` como en PHP. |
| Cliente rápido (lecturas) | GET | `/ecom/api/mayoristapp/clientes/rapido/?ajax=1&accion=…` | `inicio`, `tipoCliente`, `ivaCliente`, `provincia`, `departamento`, `distrito`, `obtieneCliente&codCliente=` (fila `SELECT *` de `cliente`). |
| Cliente rápido (lecturas) | POST | `/ecom/api/mayoristapp/clientes/rapido/?ajax=1` | `accion=altaCliente` / `editaCliente` con los mismos campos que `relay-cliente-rapido.php` (`tipoCliente`, `nombreCliente`, `tipoDocCliente`, `nroCuitCliente`, `nroDocCliente`, `ivaCliente`, `listaPrecio`, `telefonoCliente`, `faxCliente`, `emailCliente`, dirección, `codCliente` en edición). Validación `valida_cliente_existe`; `INSERT`/`UPDATE` parametrizados; `id_pc` desde `cont_paramatriz`; primera fila `cliente_domicilio` con `id_zona=1` en alta. Tras éxito: selección en sesión (`selecciona_cliente`); en alta además `session['clienteRapido']` = JSON (`actualizar_cliente_rapido`). Edición sin permiso completo (`permiso_alta_cliente` ≠ Si en `session.user`): solo teléfono, email y domicilio fiscal básico. |

---

## 4 — Pendientes

- Paridad visual/HTML de la búsqueda (en PHP era tabla); Synap entrega JSON.
- Tests con MySQL real para `CodViajante` / `todos_clientes` y escrituras de domicilio/contacto.
