# Arquitectura actual (AS-IS) — Pedidos eCom Mayorista

**Confianza global arquitectura:** CONFIRMADO (código PHP) + INFERIDO (VB6 downstream)

---

## 1. Vista de capas

```mermaid
flowchart TB
    subgraph presentacion [Capa presentación]
        UI1[alta_pedido.php]
        UI2[lista-pedidos-vendedor.php]
        UI3[ver_pedido.php]
        JS[carrito.js / jcart.js]
    end

    subgraph aplicacion [Capa aplicación PHP]
        JC[jcart/jcart.php]
        CONF1[alta_pedido_confirmado.php]
        CONF2[alta_pedido_confirmado_cliente.php]
        AJAX[ajax-comprobante.php]
        REL[relay-pedidos.php]
    end

    subgraph datos [MySQL AdministraNET]
        CM[codmov]
        TAL[talonarios]
        CP[comp_ped]
        SP[stockp]
        SD[stock_deposito]
        CDA[cliente_datos_adicionales]
        PC[percep_cli]
    end

    subgraph legacy [VB6 post-alta]
        VB6[Pedido_prep / Remito / Factura]
    end

    UI1 --> JC
    JS --> JC
    JC -->|checkout POST| CONF1
    JC -->|cliente| CONF2
    CONF1 --> CM
    CONF1 --> TAL
    CONF1 --> CP
    CONF1 --> SP
    CONF1 --> SD
    CONF1 --> CDA
    CONF1 --> PC
    UI2 --> REL
    UI2 --> UI3
    AJAX --> CP
    AJAX --> SP
    AJAX --> SD
    CP --> VB6
```

---

## 2. Secuencia de alta (CONFIRMADO)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant AP as alta_pedido.php
    participant JC as jCart
    participant AC as alta_pedido_confirmado
    participant DB as MySQL

    U->>AP: Selecciona cliente (sesión)
    U->>AP: Busca y agrega artículos
    AP->>JC: POST add/update item
    JC->>JC: update_subtotal()
    U->>JC: Confirmar pedido (checkout)
    JC->>AC: POST formaEntrega, domicilio, detalle
    Note over AC: Si tipousuario=cliente redirect a _cliente.php

    AC->>DB: TX1 loop UPDATE codmov (optimistic)
    AC->>DB: TX2 BEGIN
    AC->>DB: UPDATE talonarios PED
    AC->>DB: INSERT cliente_datos_adicionales
    AC->>DB: INSERT percep_cli (si aplica)
    AC->>DB: INSERT comp_ped Estado=Pendiente
    loop Por cada renglón
        AC->>DB: UPDATE stock_deposito saldo_pedido_cliente
        AC->>DB: INSERT stockp
    end
    AC->>DB: COMMIT o ROLLBACK
    AC->>AP: redirect alta_pedido.php?cartel=0&ped=NNNN
    AC->>JC: empty_cart()
```

---

## 3. Modelo de transacciones (CONFIRMADO)

| Fase | SQL | Propósito |
|------|-----|-----------|
| **TX-A** | `SET AUTOCOMMIT=0; BEGIN;` loop `codmov` `COMMIT/ROLLBACK` | Reservar `CodigoMovimiento` sin colisión |
| **TX-B** | `SET AUTOCOMMIT=0; BEGIN;` … `COMMIT/ROLLBACK` | Alta atómica cabecera + renglones + stock |

**Rollback parcial (CONFIRMADO):** si TX-B falla tras TX-A exitosa, se ejecutan `DELETE` manuales de `percep_cli`, `cliente_datos_adicionales`, `comp_ped` por `CodigoMovimiento` (L837-846). El `codmov` ya consumido **no se revierte**.

---

## 4. Patrón de sesión PHP

- **Sin API REST formal** — formularios POST + AJAX jQuery.
- **Estado del carrito en `$_SESSION['jcart']`** — se pierde al `empty_cart()` post-commit.
- **Multi-empresa:** conexión vía `conexion-vendedor-empresa.inc.php` según sesión vendedor.

---

## 5. Integración con VB6 (INFERIDO, documentado en reports)

```mermaid
stateDiagram-v2
    [*] --> Pendiente: Alta eCom PHP
    Pendiente --> EnPreparacion: VB6 Pedido_prep
    EnPreparacion --> Preparado: VB6 Pedido_prep
    Preparado --> EnRemito: VB6 Remito + rem_ped
    EnRemito --> Facturado: VB6 Factura + ped_fact
    Facturado --> Cerrado: VB6 cierre
    Pendiente --> Anulado: ajax-comprobante (eCom)
```

eCom PHP **solo escribe** el nodo inicial `Pendiente`. Transiciones posteriores son VB6/Synap logística.

---

## 6. Puntos de falla conocidos (CONFIRMADO)

| Punto | Riesgo |
|-------|--------|
| `codmov` consumido sin alta completa | Hueco numérico; limpieza manual DELETE |
| Stock sin check SQL | Sobre-reserva si bypass JS |
| `fin-comprobante` PED sin redirect | UX muerta tras mail |
| Filtro `TipoPedido=Web` | Listado vacío para pedidos `Ecom vendedor` |
| Anulación sin UI | Operadores dependen de VB6 u otro canal |

---

## 7. Dependencias externas

| Sistema | Interacción |
|---------|-------------|
| MySQL legacy | Persistencia única |
| SMTP vendedor (`$_SESSION['correo']`) | Mail comprobante vía `fin-comprobante` |
| Geolocalización sesión | `geo_latitud` / `geo_longitud` en `comp_ped` |
| AdministraNET desktop | Estados, remitos, facturas, preparación |
