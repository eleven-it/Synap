# Design UX — Docenas operativas y clasificación por operario fabricante (MPR)

**Change:** `mpr-docenas-clasificacion-operario`  
**Propuesta:** [proposal.md](./proposal.md)  
**Audiencia:** Operario de línea · clasificador · supervisor · analista MPR

---

## 1. Objetivo de experiencia

El operador de planta **piensa en docenas**; Synap debe mostrar y capturar en docenas por defecto, sin perder precisión en unidades en base de datos.

El clasificador debe registrar **quién fabricó** cada bulto y cómo se repartió entre Semi elaborado, 2da selección y Scrap — en una grilla densa, no con un operario fijo en cabecera.

---

## 2. Principios de diseño

| Principio | Implementación |
|-----------|----------------|
| **Docenas primero** | Default docenas en MPR operativo; unidades como modo alternativo |
| **Una verdad en BD** | Ledgers siempre en unidades; conversión solo en UI/POST |
| **Fabricante, no clasificador** | Fila = (artículo × operario que produjo en parte) |
| **Pendiente honesto** | Solo filas con pendiente > 0; arrastre de turnos visible aparte |
| **Canon MPR** | Patrones `base_app.html`, filtros `h-9`, tablas sticky, toggles como reportes |
| **Sin sorpresas** | Hint `= N u.` bajo inputs en docenas; bloqueo claro si falta parte por operario |

---

## 3. Toggle global Docenas / Unidades

### Ubicación

Barra de contexto MPR operativo (tablero, envío, parte, clasificación) — mismo patrón que chips `Unid|Doc` en reportes stock.

### Comportamiento

| Estado | Efecto |
|--------|--------|
| **Docenas** (default) | Columnas numéricas en docenas enteras; inputs principales en docenas |
| **Unidades** | Comportamiento actual (enteros u.) |
| Persistencia | `request.session['mpr_presentacion_cantidad']` |
| Alcance | Solo pantallas operativas MPR en este change; reportes P1 |

### Componente

`mpr/templates/mpr/includes/toggle_presentacion_cantidad.html` — POST o query `?presentacion=docenas|unidades` con CSRF.

---

## 4. Tablero consolidado

### Columnas (modo docenas)

| Columna | Presentación |
|---------|----------------|
| Pendiente | `542` doc. (o `542 doc. + 6 u.` si resto) |
| En producción / Semi / … | Docenas enteras; sublínea unidades si resto ≠ 0 |
| **Enviar** | Input docenas (required) + input unidades (opcional, visible si usuario expande o resto) |
| Hint | `= 6502 u.` bajo el input al cambiar |

### Envío POST

Servidor convierte `docenas + unidades_sueltas` → `cantidad` unidades antes de `registrar_envio_produccion`.

---

## 5. Parte de producción

- Respeta toggle global (no toggle local duplicado).
- Captura principal: **docenas** por celda operario × componente.
- Unidades sueltas: campo secundario colapsable o segunda columna estrecha.
- Sin cambio de modelo: `mpr_parte_linea.cantidad` en unidades.

---

## 6. Clasificación por operario fabricante

### Layout

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Clasificación de producción · Turno Mañana · 08/07/2026    [Docenas|Unid]   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Filtros: fecha · turno · búsqueda artículo                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▼ Turno actual — pendiente por operario                                       │
│ ┌─────────────┬──────────┬────────────┬──────┬──────┬──────┬──────────────┐ │
│ │ Artículo    │ Operario │ En prod.   │ Semi │ 2da  │Scrap │ Pendiente    │ │
│ ├─────────────┼──────────┼────────────┼──────┼──────┼──────┼──────────────┤ │
│ │ 12A-PRV-01  │ García   │  45 doc.   │ [__] │ [__] │ [__] │  45 doc.     │ │
│ │ Pack básico │ López    │  38 doc.   │ [__] │ [__] │ [__] │  38 doc.     │ │
│ └─────────────┴──────────┴────────────┴──────┴──────┴──────┴──────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▼ Pendiente de turnos anteriores (solo lectura + acción «Clasificar»)        │
│ … filas con arrastre …                                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Columnas

| Columna | Tipo | Notas |
|---------|------|-------|
| Artículo | Lectura | `id_manual - CodArtProv` (filtro `codigo_mpr`) |
| Operario | Lectura | Nombre desde parte |
| En producción | Lectura | Saldo atribuible al operario (docenas) |
| Semi / 2da / Scrap | Input | Docenas (+ unidades opc.) |
| Pendiente | Lectura | `en_prod − (semi+2da+scrap)` del turno |

### Validaciones UX

- Por fila: `semi + 2da + scrap ≤ en_producción_operario`.
- Global artículo: `Σ operarios clasificado ≤ stock Producción`.
- Si parte del artículo no tiene operarios: banner error + enlace a Parte.

### P1 — Ver roster completo

Toggle supervisor muestra filas con pendiente 0 (solo lectura de histórico del turno).

---

## 7. Reporte rendimiento por operario

Extiende `/mpr/reportes/.../operario` (o slug existente):

| Columna | Fuente |
|---------|--------|
| Operario | `mpr_parte_linea` |
| Fabricado (doc.) | Σ parte |
| Semi / 2da / Scrap (doc.) | Σ `mpr_transicion_lote` con `id_operario` |
| % Apto | semi / fabricado |
| % Scrap | scrap / fabricado |

Filtros: rango fechas, turno opcional, marca.

---

## 8. Esquema de datos

### `mpr_transicion_lote` (ALTER)

| Columna | Tipo | Notas |
|---------|------|-------|
| `id_operario` | INT NULL | FK lógica `operario.id_operario` — **fabricante** |
| `operario_nombre` | VARCHAR | Snapshot nombre al guardar |

Índice sugerido: `(fecha, id_turno, id_articulo, id_operario, tipo_destino)`.

Histórico: `id_operario IS NULL` → reportes muestran «Sin atribución».

---

## 9. Componentes reutilizados

| Componente | Origen |
|------------|--------|
| Toggle Unid/Doc | `mpr/reportes/_filtros.html` |
| `texto_docenas_unidades` | `mpr/services.py` |
| Tabla sticky | `clasificacion_produccion.html`, `tablero_produccion.html` |
| Toggle Activo/Inactivo patrón | usuarios/sucursales (solo referencia de estilo) |

---

## 10. Accesibilidad y errores

- Mensajes en español: «La suma por operario no puede superar lo fabricado en parte».
- Fechas al usuario: **dd/MM/yyyy**.
- Inputs numéricos `inputmode="numeric"`, `min="0"`, `step="1"` en docenas.
