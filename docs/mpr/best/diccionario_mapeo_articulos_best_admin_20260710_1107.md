# Diccionario de mapeo BEST → AdministraNET (artículos)

**Versión:** 2026-07-10-v3
**Fecha:** 10/07/2026 11:07
**Modo:** solo lectura — no modifica DBs
**Propósito:** desbloquear cutover de pedidos abiertos BEST → PED MPR

## Reglas confirmadas

### Talle
| Admin | BEST |
|-------|------|
| TL | 4 |
| TM | 5 |
| T1..T6 | 1..6 |
| T110 / T120 / T130 | 4 / 5 / 6 |

### Color (código BEST → palabras Admin)
BL→Blanco; NE→Negro; GM/GR→Gris/Gmel; MN→Marino/Mno; M4; FU→Fucsia; RO→Rojo; AZ→Azul; VE→Verde; RS→Rosa; CR→Crudo; BE→Beige; MA→Marrón; SU/AO/AE/GT literales.

### Modos (crítico para 1:1)
| BEST | Admin pack 2P/3P | Evitar |
|------|------------------|--------|
| Colores iguales (BL/BL) | Sólido + mismo pack | Mix; 1Par Logo |
| Colores distintos (BL/NE) | **Mix** + mismo pack | Sólido; 1Par Logo (salvo revisión) |
| PACK 2/3 | 2P/3P | **1Par** (otra SKU) |

### Alias de modelo
Además del MMID/Codigo, se indexan **todos los números 3–6 dígitos** de la descripción BEST
(ej. `PUMA 2574-02` con codigo `7312` → busca también `2574`;
`Levis (7862)7864-M004` → `7862` y `7864`; `Puma 7571-01` con codigo `7471` → `7571`).

### Variante comercial
`7944-02` ↔ `907944-02` / `7944-02` en nombre o `CodArtProv`.

### Desempate
Si dos `IDArt` tienen el **mismo nombre** y mismo score (duplicado de alta), se elige el `IDArt` menor y **no** se marca AMBIGUO.
