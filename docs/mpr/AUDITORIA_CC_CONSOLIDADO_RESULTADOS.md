# Auditoría baseline CC consolidado — resultados

**Fecha:** 20/08/2026  
**Procedimiento:** `docs/mpr/AUDITORIA_CC_CONSOLIDADO_BASELINE.sql` (solo SELECT, plan §12.3)

---

## 1. MySQL local (contenedor `Synap_mysql57`)

| Base | `mpr_transicion_lote` |
|------|------------------------|
| `administranet` | No existe |
| `administranet92` | No existe |

N/A para conteos. I3 cubierto por test S8.

---

## 2. Empresa de prueba — Server2 (20/08/2026, pre primer confirm nuevo)

| Campo | Valor |
|-------|--------|
| Host | `181.174.198.194:30804` (hostname MySQL: **Server2**) |
| Base | `administranet1` (Prueba) |
| `mpr_transicion_lote` | Sí (4231 filas totales) |
| `mpr_clasificacion_borrador` (006) | Sí |
| `mpr_cc_borrador` / `_linea` (007) | Creadas en este corte |

### 2.1 Query A — histórico CC (`tipo_origen = Produccion`)

| tipo_destino | con_operario | sin_operario | filas | qty |
|--------------|--------------|--------------|-------|-----|
| SemiElaborado | 3669 | **0** | 3669 | 268969 |
| 2daSeleccion | 534 | 0 | 534 | 4227 |
| Scrap | 28 | 0 | 28 | 94 |

**Corte:** no hay Semi `id_operario NULL` todavía. Tras confirmar CC nuevo, `sin_operario` de Semi debe subir y `con_operario` **no debe bajar**.

### 2.2 Query B — top saldo Depósito Producción

Join real: `deposito.CodDeposito` + `stock_deposito.saldo` (no `cantidad` / `id_deposito` en cabecera).

| IDArt | Código | Artículo | Saldo Producción |
|-------|--------|----------|------------------|
| 890 | 1.1.886 | 6807 T5 Puma Negro/Blanco 1Par | 8172 |
| 889 | 1.1.885 | 6807 T5 Puma Blanco/Negro 1Par | 6468 |
| 962 | 1.1.958 | 7944 T5 Puma Negro Logo Blanco 1Par | 5634 |
| 902 | 1.1.898 | 6978 T5 Puma Negro/Blanco 1Par | 4584 |
| 891 | 1.1.887 | 6807 T5 Puma Gmel/Negro 1Par | 3510 |

Candidatos para humo: un bloque con saldo alto; Semi único; 2da por operario del parte del día.

### 2.3 DDL aplicado

- `idx_mpr_tl_fecha_art_dest` en `mpr_transicion_lote`
- `mpr_cc_borrador` + `mpr_cc_borrador_linea`
- Primer intento de 007 falló: UK/FK `uk_mpr_cc_borrador_linea` ya existían en tablas **006**. SQL corregido a `uk_mpr_cc_borrador_cons_linea` / `fk_mpr_cc_borrador_cons_linea_cab`.
- Re-run `run_mpr_core_tables_mysql`: **success**, failed=[]

**No se tocó** `administranet` (producción).
