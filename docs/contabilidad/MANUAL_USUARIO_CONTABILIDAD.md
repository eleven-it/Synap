# Manual de usuario – Contabilidad (Auditoría)

Guía práctica del módulo **Contabilidad** en Synap para contadores, supervisores y operadores que auditan y corrigen la imputación contable legacy (AdministraNET).

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar. La empresa del tablero y del dry-run es **siempre la de su sesión** (no se puede cambiar por la URL).

**Manual HTML en la app:** **`/contabilidad/manual/`** (requiere sesión). En las pantallas del módulo hay un botón **Ayuda** que abre este manual. Regenerar HTML: `python3 scripts/generar_manuales_html.py`.

**Fechas en pantalla:** siempre en formato **dd/MM/yyyy**.

---

## 1. Acceso al módulo

1. En el menú de Synap, abra **Contabilidad**.
2. Pantallas habituales:

| Pantalla | Menú / ruta | Permiso típico |
|----------|-------------|----------------|
| **Tablero de auditoría** | Contabilidad → Tablero de auditoría | `contabilidad.auditoria.leer` |
| **Configuración de políticas** | Contabilidad → Configuración de políticas | `contabilidad.auditoria.configurar` (editar) |
| **Dry-run de corrección** | Desde el tablero → Generar dry-run | Lectura |
| **Aplicar corrección** | Desde el dry-run | `contabilidad.auditoria.corregir` |
| **Lotes aplicados** | Enlace en el tablero / dry-run | Lectura; rollback requiere corregir |
| **Manual de usuario** | Contabilidad → Manual de usuario, o **Ayuda** | Sesión activa |

---

## 2. Conceptos clave

### Diagnóstico vs corrección

| Acción | ¿Escribe en MySQL legacy? | Para qué sirve |
|--------|---------------------------|----------------|
| **Ejecutar auditoría** (tablero) | No | Solo lectura: detecta diferencias |
| **Generar dry-run** | No | Arma un **plan** de corrección (se guarda en Synap/Postgres) |
| **Aplicar corrección** | **Sí** | Ejecuta el plan (backup + escritura + log) |
| **Revertir lote** | **Sí** | Restaura tablas desde el backup del lote |

### Modal de espera

Las operaciones largas muestran un **modal de espera** con título y estado (por ejemplo «Ejecutando auditoría», «Generando dry-run», «Aplicando corrección contable»). **No cierre** la ventana del navegador mientras el modal esté visible.

### Regeneración y saldos

Cuando el plan regenera asientos faltantes (compras/pagos o ventas/cobranzas), **también incluye el recálculo de saldos** del ejercicio en alcance (tablas de saldo de ejercicio y, si aplica, de período). En el dry-run verá impacto en `cont_asiento` y en las tablas de saldo.

---

## 3. Tablero de auditoría

**Menú:** Contabilidad → Tablero de auditoría.

### Para qué sirve

Correr los **checks de integridad** contable sobre la base legacy de la empresa de sesión y ver, por check, si está OK (verde) o con diferencias (rojo).

### Cómo usarlo

1. Elija **Ejercicio** (obligatorio) y, si quiere, **Período** (opcional). Ambos tienen búsqueda predictiva.
2. Opcionalmente filtre qué checks ejecutar (por defecto se evalúan todos).
3. Pulse **Ejecutar auditoría**. Aparecerá el modal «Ejecutando auditoría».
4. Revise las tarjetas: cantidad de diferencias, severidad (Crítico / Alto / Medio).
5. Abra una tarjeta con diferencias para ver el detalle.
6. Puede exportar **CSV** o **Excel** del resultado.

### Comprobantes sin asiento (huérfanos)

Dos checks críticos listan comprobantes con `CodigoMovimiento` sin filas en `cont_asiento`:

| Check | Tabla | Tipos | Contabilidad activa |
|-------|-------|-------|---------------------|
| Compra/pago sin asiento | `cuentaproveedor` | FA, FC, OP | Sucursal con contabilidad (`sucursales.cont = Si`) |
| Venta/cobranza sin asiento | `cuentacliente` | FA, FB, FC, FE, FM, REC | Punto de venta con contabilidad (`punto_venta.cont = Si`) |

En el detalle de cada uno:

- Ve tipo, nro. de comprobante, fecha, importe, sucursal, P.V. y código de movimiento.
- Pulse **Generar dry-run de regeneración** para armar el plan (modal «Generando dry-run»). También puede usar **Generar dry-run** del encabezado.

### Avisos frecuentes

- «Ingresá empresa y ejercicio»: falta el ejercicio o no hay empresa en sesión.
- Tarjeta en ámbar con «Error: …»: falló ese check (conexión o SQL); el resto puede haberse evaluado.
- Cero diferencias: el check está OK para el alcance elegido.

---

## 4. Dry-run (plan de corrección)

**Cómo llegar:** desde el tablero (enlaces de dry-run) o la URL de dry-run con ejercicio.

### Para qué sirve

Generar un plan **sin escribir** en legacy: regeneración de asientos, reparación de anulaciones incompletas (compra/pago), ajustes de concepto, filas de saldo faltantes y **recompute de saldos**.

### Cómo usarlo

1. Confirme empresa (sesión), ejercicio y período opcional.
2. Pulse **Generar dry-run** (modal de espera).
3. Revise:
   - **Guards** del plan (TTL, huella de configuración y de datos).
   - **Asientos huérfanos a regenerar** (FA/FC/OP y FA/FB/…/REC según corresponda).
   - Impacto por tabla.
   - Anulaciones reparables / bloqueadas (si aplica).
4. Si el plan está vacío: el alcance no tiene correcciones automáticas (o ya están aplicadas); el tablero puede seguir en rojo por checks que no entran al dry-run.
5. Si hay ítems aplicables y tiene permiso de corregir, continúe a **Aplicar** (también en development para pruebas).

### Advertencia de performance

Si la política de alcance es **histórico**, el dry-run puede tardar mucho. Prefiera ejercicio seleccionado y ejecutar fuera del horario pico.

### Export

Desde el dry-run puede descargar el plan en CSV o Excel.

---

## 5. Aplicar corrección

**Requisitos:**

- Permiso `contabilidad.auditoria.corregir` (válido en development y producción).
- Plan de dry-run vigente (dentro del TTL y con la misma huella de datos).
- Confirmación explícita en la UI (checkbox).

### Cómo usarlo

1. Desde el dry-run, abra la confirmación de apply.
2. Lea el resumen (única acción que escribe en MySQL legacy).
3. Marque la confirmación y pulse **Aplicar corrección definitivamente**. Verá el modal «Aplicando corrección contable…».
4. Al terminar, anote el **lote** generado para eventual rollback.

### Qué hace el apply (orden)

1. Regenera asientos faltantes (compras/pagos y ventas/cobranzas).
2. Repara anulaciones incompletas de compra/pago (si el plan las incluye).
3. Ajusta conceptos de anulación incoherentes.
4. Inserta filas de saldo faltantes.
5. Actualiza saldos de ejercicio/período.

Cada apply crea **backup** previo de las tablas tocadas y deja log en `cont_audit_correccion_lote` / `cont_audit_correccion`.

---

## 6. Lotes aplicados y rollback

**Cómo llegar:** enlace **Lotes aplicados** en el tablero o dry-run.

### Para qué sirve

Ver los lotes de corrección ya aplicados y, si corresponde, **revertir** uno restaurando desde su backup.

### Cómo revertir

1. Ubique el lote (estado aplicado).
2. Pulse revertir y confirme en el **modal Synap** (no use diálogos del navegador).
3. Aparecerá el modal de espera «Revirtiendo lote».
4. El lote queda marcado como revertido.

El rollback requiere permiso de corregir (también en development). Si falta alguna tabla de backup, la operación se aborta sin cambios parciales.

---

## 7. Configuración de políticas

**Menú:** Contabilidad → Configuración de políticas.

### Para qué sirve

Definir cómo se interpretan anulados, centavos, prefijos de cuenta, ejercicios cerrados, alcance del recálculo y tolerancia decimal. Puede haber política global y override por empresa.

### Cómo usarlo

1. Elija la base (global o empresa) si tiene permiso de configurar.
2. Ajuste los campos y guarde.
3. Consulte el **historial de cambios** (quién cambió qué y cuándo, fechas dd/MM/yyyy).

Sin permiso de configurar verá la pantalla en **solo lectura**.

---

## 8. Aprobación REI (casos especiales)

Algunos hallazgos de **REI** (ajuste por inflación) requieren aprobación caso a caso antes de un apply en modo REI.

1. Genere el dry-run que incluya propuestas REI.
2. Abra la pantalla de aprobación REI del plan.
3. Apruebe o rechace cada caso (permiso `contabilidad.auditoria.rei`).
4. Solo entonces podrá aplicar en modo REI desde la pantalla de apply.

---

## 9. Permisos (resumen)

| Permiso | Qué habilita |
|---------|----------------|
| `contabilidad.auditoria.leer` | Tablero, dry-run, lotes (consulta), ver configuración |
| `contabilidad.auditoria.configurar` | Editar políticas |
| `contabilidad.auditoria.corregir` | Apply y rollback (cualquier entorno) |
| `contabilidad.auditoria.rei` | Aprobar/rechazar REI |

Si no ve un botón o recibe error de permiso, solicite el alta al administrador Synap.

---

## 10. Problemas frecuentes

| Situación | Qué hacer |
|-----------|-----------|
| El tablero sigue en rojo después de un dry-run vacío | El dry-run solo cubre ciertos checks; vuelva a **Ejecutar auditoría** para refrescar. Un plan en Postgres no cambia el diagnóstico hasta el **apply**. |
| «Generar dry-run» tarda mucho y no veía aviso | Debe aparecer el modal de espera; si no, recargue la página (versión actualizada) y reintente. |
| Apply rechazado por permiso | Solicite `contabilidad.auditoria.corregir` al administrador. |
| Apply pide confirmar | Debe marcar el checkbox de confirmación antes de aplicar. |
| Huérfanos de venta = 0 pero había muchos | Las ventas usan gating por **punto de venta** (`cont = Si`), no por sucursal. |
| Regeneré asientos y cambiaron saldos | Es esperado: el plan encadena recálculo de saldos del ejercicio. |
| Rollback no disponible | Verifique permiso de corregir y que el lote tenga backups intactos. |

---

## 11. Resumen rápido por rol

**Consulta / auditoría diaria**

1. Tablero → ejercicio → Ejecutar auditoría.  
2. Revisar checks críticos (huérfanos, saldos, anulaciones).  
3. Exportar si necesita llevar el detalle a Excel.

**Corrección de asientos faltantes**

1. Abrir el check de huérfanos → Generar dry-run de regeneración.  
2. Revisar asientos a regenerar y impacto en saldos.  
3. Apply con confirmación (permiso de corregir).  
4. Guardar el id de lote; re-ejecutar auditoría para verificar verdes.

**Administración**

1. Configurar políticas (alcance, tolerancia, ejercicios cerrados).  
2. Revisar historial de políticas y lotes aplicados.  
3. Coordinar rollbacks solo cuando sea necesario.

---

_Documentación técnica (equipo desarrollo): `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md`._
