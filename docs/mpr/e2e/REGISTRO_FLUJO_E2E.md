# Registro E2E — Flujo MPR demanda → OPT → OPP

> Manual visual HTML: [MANUAL_USUARIO_MPR.html](MANUAL_USUARIO_MPR.html)

> **Flujo diario (tablero → imputación):** ver [REGISTRO_FLUJO_DIARIO_E2E.md](REGISTRO_FLUJO_DIARIO_E2E.md) y comando `e2e_mpr_trazabilidad`.

Generado: 29/6/2026, 09:11:21

| Paso | Pantalla | Validación | Captura |
|------|----------|------------|---------|
| 1 | Tablero de control | KPIs y accesos rápidos visibles | [01-tablero-inicial.png](capturas/01-tablero-inicial.png) |
| 2 | Demanda (ventana pack) | Tabla de packs con demanda | [02-demanda-ventana-pack.png](capturas/02-demanda-ventana-pack.png) |
| 3 | Selección en demanda | Artículo 490, cantidad 10 | [03-demanda-fila-seleccionada.png](capturas/03-demanda-fila-seleccionada.png) |
| 4 | Confirmar OPT | — | [04-confirmar-opt.png](capturas/04-confirmar-opt.png) |
| 5 | Detalle OPT | OPT creada/liberada | [05-opt-detalle-post-generar.png](capturas/05-opt-detalle-post-generar.png) |
| 6 | Formulario OPP | — | [06-opp-formulario-completo.png](capturas/06-opp-formulario-completo.png) |
| 7 | OPP registrada | Sin modal de error OPP | [07-opp-registrada.png](capturas/07-opp-registrada.png) |
| 8 | Tablero (validación post-OPP) | Movimientos recientes / OPTs en proceso actualizados | [08-tablero-post-opp.png](capturas/08-tablero-post-opp.png) |
| 9 | Listado OPT | OPT 10 visible en listado | [09-listado-opt.png](capturas/09-listado-opt.png) |
| 10 | Detalle OPT (cierre de recorrido) | Trazabilidad OPT/OPP visible | [10-opt-detalle-final.png](capturas/10-opt-detalle-final.png) |

## Detalle por paso

### 1. Tablero de control
- **Ruta:** `/mpr/`
- **Validación:** KPIs y accesos rápidos visibles
- **Notas:** Punto de entrada al módulo MPR (Manual §2).
- **Captura:** `docs/mpr/e2e/capturas/01-tablero-inicial.png`

### 2. Demanda (ventana pack)
- **Ruta:** `/mpr/demanda/ventana-pack/`
- **Validación:** Tabla de packs con demanda
- **Notas:** Manual §3.1. Pestaña Packs; marcar fila y cantidad a fabricar.
- **Captura:** `docs/mpr/e2e/capturas/02-demanda-ventana-pack.png`

### 3. Selección en demanda
- **Ruta:** `/mpr/demanda/ventana-pack/`
- **Validación:** Artículo 490, cantidad 10
- **Captura:** `docs/mpr/e2e/capturas/03-demanda-fila-seleccionada.png`

### 4. Confirmar OPT
- **Ruta:** `/mpr/demanda/ventana-pack/agrupar/`
- **Notas:** Manual §3.1.1. Revisar cantidades por componente BOM.
- **Captura:** `docs/mpr/e2e/capturas/04-confirmar-opt.png`

### 5. Detalle OPT
- **Ruta:** `http://localhost:8000/mpr/opt/10/`
- **Validación:** OPT creada/liberada
- **Captura:** `docs/mpr/e2e/capturas/05-opt-detalle-post-generar.png`

### 6. Formulario OPP
- **Ruta:** `/mpr/wizard/?paso=3&id_lista=10`
- **Notas:** Distribución a Semi elaborado; operario por fila.
- **Captura:** `docs/mpr/e2e/capturas/06-opp-formulario-completo.png`

### 7. OPP registrada
- **Ruta:** `http://localhost:8000/mpr/wizard/?paso=3&id_lista=10`
- **Validación:** Sin modal de error OPP
- **Captura:** `docs/mpr/e2e/capturas/07-opp-registrada.png`

### 8. Tablero (validación post-OPP)
- **Ruta:** `/mpr/`
- **Validación:** Movimientos recientes / OPTs en proceso actualizados
- **Notas:** Manual §2 — revisar panel OPTs en proceso y movimientos.
- **Captura:** `docs/mpr/e2e/capturas/08-tablero-post-opp.png`

### 9. Listado OPT
- **Ruta:** `/mpr/opt/`
- **Validación:** OPT 10 visible en listado
- **Captura:** `docs/mpr/e2e/capturas/09-listado-opt.png`

### 10. Detalle OPT (cierre de recorrido)
- **Ruta:** `/mpr/opt/10/`
- **Validación:** Trazabilidad OPT/OPP visible
- **Notas:** Manual §6 — OPPs vinculadas, pendientes, armado.
- **Captura:** `docs/mpr/e2e/capturas/10-opt-detalle-final.png`
