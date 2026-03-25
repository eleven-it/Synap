# Auditoría: Facturas de compras — Pendientes, dudas y supuestos

**Convención:** *Confirmado por código* | *Inferencia fuerte* | *Hipótesis / pendiente*

---

## 1. SQL y precedencia de operadores

### 1.1 `DELETE` en `Elimina_Temporal` (`serie_entrada_temp`)

**Código:** `PFactura.frm` ~7780–7783:

```text
DELETE FROM serie_entrada_temp 
WHERE id_usuario = … AND visualiza = 'No' AND tipo_comprobante = 'PFactura' OR tipo_comprobante = 'PRemito'
```

**Duda:** En SQL estándar, el `OR` puede aplicarse de forma que borre filas `PRemito` de **otros usuarios** si no hay paréntesis explícitos.

- **Clasificación:** *Hipótesis / pendiente* hasta ejecutar el mismo SQL en el motor y ver plan o probar datos.
- **Acción:** Verificar en MySQL y/o corregir en Synap con paréntesis explícitos si se confirma el riesgo.

---

## 2. Validación de duplicados sin FM

**Evidencia:** `Validacion_Comp` usa `(TipoComprobante = 'FA' or 'FC' or 'FB')` — no incluye `FM`.

- **Duda:** ¿Es omisión intencional o bug legacy?
- **Clasificación:** *Confirmado por código* (omisión); intención *hipótesis débil*.

---

## 3. Limpieza de `en_vale_factura_temp` tras guardar

**Evidencia en `PFactura.frm`:** solo aparecen `SELECT` e `INSERT…SELECT` hacia `en_vale_factura` (~3571, ~3849, ~3857). **No hay** `DELETE` sobre `en_vale_factura_temp` en este formulario (búsqueda por nombre de tabla en el archivo).

- **Duda:** ¿Quién vacía la temp? ¿`Principal`, `En_Liquidacion_Vales`, cierre de sesión, o queda hasta que el usuario vuelva a liquidar vales?
- **Clasificación:** *Pendiente* — barrer todo `administranet_vb6` (incl. `.frm` con codificación que a veces impide búsqueda por carpeta) y/o rutinas MySQL.

---

## 4. Libro IVA compras

**Evidencia:** No hay tabla con nombre explícito en `PFactura.frm`.

- **Inferencia fuerte:** Los datos para libro IVA digital salen de `cuentaproveedor` / `stock` + exportaciones (`Exportacion.frm` u otros).
- **Pendiente:** Mapear reportes/procedimientos MySQL o vistas usadas en exportación AFIP.

---

## 5. Triggers y reglas en base de datos

**Pendiente:** Inspección de DDL MySQL del cliente para triggers en `stock`, `cuentaproveedor`, etc., que el VB6 no muestre.

---

## 6. `modificacion_comp` — alcance incompleto en auditoría

**Confirmado:** Actualiza fechas/número/proyecto en varias tablas.

**Pendiente:** Si al modificar se debe recalcular asientos, IVA o stock, no aparece en el fragmento ~7894–8149; podría existir otra ruta o limitación funcional legacy.

---

## 7. `DELETE serie_entrada_temp` al cancelar renglón (~6705)

**Revisado:** el `DELETE` al borrar un renglón usa solo condiciones con `AND` (`id_articulo`, `visualiza`, `id_usuario`, `tipo_comprobante`, `orden`) — `PFactura.frm` ~6705–6709. **No** presenta el mismo riesgo de precedencia que `Elimina_Temporal`.

---

## 8. Código comentado en `Guardar`

Bloques comentados de percepciones por provincia (~3931–3971) y otras ramas pueden reflejar reglas viejas.

- **Clasificación:** *Hipótesis débil* — no activos en runtime.

---

## 9. Supuestos explícitos del equipo de migración

1. `Principal.*` tiene equivalente en configuración Synap por empresa/sucursal/usuario.  
2. `IngresoUsuario.Conex` apunta al mismo schema MySQL que consumirá Django.  
3. No hay otra aplicación incrementando `codmov` con otra semántica.

---

## 10. Checklist de verificación posterior

- [ ] Grep archivo por archivo `en_vale_factura_temp` en `administranet_vb6` (si el grep por carpeta falla por encoding).  
- [ ] Probar precedencia del DELETE `serie_entrada_temp` en `Elimina_Temporal` en MySQL 5.x/8.x del cliente.  
- [ ] Extraer lista completa de campos `stock.AddNew` en `PFactura.frm` (bloque ~4200–4645) y cruzar con DDL.  
- [ ] Revisar `Lista_Comp_Gral.frm` para confirmar todos los campos copiados a `cuerpostockp`.
