# Seguridad y permisos — Pedidos eCom (AS-IS)

**Modelo:** Sesión PHP server-side, sin JWT ni RBAC granular en eCom.  
**Confianza:** CONFIRMADO (sesión) + INFERIDO (flags empresa)

---

## 1. Autenticación (CONFIRMADO)

| Mecanismo | Detalle |
|-----------|---------|
| Login | `index.php` → sesión PHP estándar |
| Persistencia | `sesion.inc.php` + cookies sesión |
| Tipos usuario | `tipousuario`: `vendedor` \| `cliente` |
| Multi-empresa | Conexión MySQL por empresa del vendedor |

**Control horario:** Código comentado en confirmados (`fn_control_horario`) — **NO activo** en eCom pedidos (CONFIRMADO L82-86).

---

## 2. Autorización por actor (CONFIRMADO)

### Vendedor

| Capacidad | Condición sesión |
|-----------|------------------|
| Alta pedido | Cliente en sesión + acceso módulo eCom |
| Ver todos los clientes | `todos_clientes == 'Si'` |
| Ver solo cartera | `todos_clientes == 'No'` → filtro `CodViajante` |
| Listado pedidos cliente filtrado | `listaPed=cliente` + `idcliente` |

### Cliente autogestión

| Capacidad | Condición |
|-----------|-----------|
| Alta pedido | `tipousuario=cliente`, su `idcliente` |
| Listado | `comp_ped.Codigo = idcliente` |

---

## 3. Permisos de negocio en sesión (INFERIDO / CONFIRMADO parcial)

| Flag sesión | Efecto en pedidos | Evidencia |
|-------------|-------------------|-----------|
| `todos_clientes` | Alcance listado | lista-pedidos L29-31 CONFIRMADO |
| `utiliza_bulto_cerrado` | UI unidad display/bulto | alta_pedido L41-43 CONFIRMADO |
| `utiliza_display` | UI display | L46-48 CONFIRMADO |
| `utilizaEmbalaje` | Campos embalaje stockp | confirmado L584+ CONFIRMADO |
| `activ_logistica` | Hoja ruta en carrito | CONFIRMADO |
| `obliga_domicilio_cliente` | Validación domicilio jCart | INFERIDO jcart display |
| `agente_percep` | Cálculo percepciones | jcart CONFIRMADO |
| `usa_id_manual` | Formato nombre cliente listado | CONFIRMADO |
| `permiso-sin-stock` (form) | Bypass validación stock JS | carrito.js INFERIDO |

### Permisos objeto vendedor (CONFIRMADO en jCart)

| Propiedad `objVendedor` | Uso |
|-------------------------|-----|
| `mod_descuento_pie` | Editar descuento pie carrito |
| `descuento_cv` | Aplicar desc desc condición venta |
| `lim_desc_pie` | Tope descuento pie |
| `id_punto_venta` | Talonario y PV pedido |

---

## 4. Seguridad SQL (CONFIRMADO — hallazgos)

| Aspecto | Estado AS-IS | Riesgo |
|---------|--------------|--------|
| Concatenación SQL | Variables interpoladas en queries | SQL injection si entrada no sanitizada |
| API anulación | `codMovP` desde REQUEST directo | IDOR si sin validación sesión |
| CSRF | Token `jcartToken` en carrito | Parcial |

**Nota:** Análisis de hardening fuera alcance AS-IS; registrar para TO-BE.

---

## 5. Validación sesión en alta (CONFIRMADO)

```php
if (!isset($_SESSION['cliente'])) {
    header('Location:listado-clientes.php?frm=0&cartel=1');
}
```

Redirect cliente no seleccionado — no hay pedido anónimo.

---

## 6. Geolocalización (CONFIRMADO)

- Coordenadas desde `$_SESSION['latitud']` / `longitud`.
- Default `"0"` si ausente.
- Persistidas en `comp_ped` — trazabilidad operativa INFERIDO.

---

## 7. Mail y credenciales (CONFIRMADO)

- `fin-comprobante.php` exige `$_SESSION['correo']` con usuario/pass SMTP vendedor.
- Sin credenciales → bloqueo envío (`cartel=7`).

---

## 8. Anulación — control acceso (INFERIDO)

- `ajax-comprobante.php` incluye `sesion.inc.php`.
- **NO VERIFICADO:** validación explícita de que `codMovP` pertenece al vendedor/cliente de sesión.
- Listado no expone botón — reduce superficie UI.

---

## 9. Equivalencia Synap (referencia TO-BE)

| PHP sesión | Synap permiso |
|------------|---------------|
| Acceso eCom vendedor | `ecom.carrito.editar` / `ecom.pedidos.crear` |
| Ver listado | `ecom.comprobantes.ver` / `ecom.pedidos.ver` |
| Ver todos | `ecom.pedidos.ver_todos` / `todos_clientes` |
| Anular | `ecom.comprobantes.anular` |

Synap añade RBAC Django + API autenticada — ver `11` en SPEC_GESTION_PEDIDOS_SYNAP.

---

## 10. Matriz permiso × operación

| Operación | Vendedor | Cliente | Gerencia | API AJAX |
|-----------|----------|---------|----------|----------|
| Alta | ✅ | ✅ | INFERIDO | — |
| Listado propio | ✅ | ✅ | — | relay |
| Listado total | Si flag | ❌ | ✅ | relay |
| Ver detalle | ✅ | ✅ | ✅ | ver_pedido |
| Anular | INFERIDO | ❌ | INFERIDO | ajax-comprobante |
