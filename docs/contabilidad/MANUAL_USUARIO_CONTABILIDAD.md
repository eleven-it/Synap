# Manual de usuario – Contabilidad (Auditoría)

Guía práctica del módulo **Contabilidad** en Synap para contadores, supervisores y operadores que auditan y corrigen la imputación contable legacy (AdministraNET).

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar. La empresa del tablero y del diagnóstico de corrección es **siempre la de su sesión** (no se puede cambiar por la URL).

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
| **Diagnóstico de corrección** | Desde el tablero → tarjeta con diferencias → **Generar diagnóstico** | Lectura |
| **Aplicar corrección** | Desde el diagnóstico | `contabilidad.auditoria.corregir` |
| **Lotes aplicados** | Enlace en el tablero / diagnóstico | Lectura; rollback requiere corregir |
| **Eliminar asientos** | `/contabilidad/auditoria/asientos/` | Lectura + vista previa; eliminar requiere corregir |
| **Manual de usuario** | Contabilidad → Manual de usuario, o **Ayuda** | Sesión activa |

---

## 2. Conceptos clave

### Diagnóstico vs corrección

| Acción | ¿Escribe en MySQL legacy? | Para qué sirve |
|--------|---------------------------|----------------|
| **Ejecutar** (tablero) | No | Solo lectura: detecta diferencias y arma el tablero de tarjetas |
| **Generar diagnóstico** | No | Arma un **plan** de corrección de **un** diagnóstico (se guarda en Synap/Postgres) |
| **Aplicar corrección** | **Sí** | Ejecuta el plan (backup + escritura + log) |
| **Revertir lote** | **Sí** | Restaura tablas desde el backup del lote |

### Flujo obligatorio

El diagnóstico de corrección **siempre** se abre desde una tarjeta del tablero, nunca de forma global:

1. **Tablero** → elija ejercicio y diagnósticos → **Ejecutar**.
2. Aparece el **tablero de tarjetas** (una por diagnóstico) con su cantidad de diferencias.
3. En la tarjeta que tenga diferencias, pulse **Generar diagnóstico**: se calcula el plan **solo de ese** diagnóstico.

Por eso el encabezado del tablero ya **no** tiene un botón global de generación: sus acciones son **Ejecutar**, **Ayuda**, **Configuración**, **Lotes** y **Excel**.

### Cuándo una tarjeta no ofrece «Generar diagnóstico»

| Situación de la tarjeta | Qué ve |
|-------------------------|--------|
| **0 diferencias** (verde) | Ningún botón: no hay nada que corregir |
| Diferencias, pero el diagnóstico **no tiene corrección automática** | Texto discreto **«Sin corrección automática»** |
| Diferencias y corrección automática disponible | Botón **Generar diagnóstico** |

### Modal de espera

Las operaciones largas muestran un **modal de espera** con título y estado (por ejemplo «Ejecutando auditoría», «Generando diagnóstico…», «Aplicando corrección contable»). **No cierre** la ventana del navegador mientras el modal esté visible.

### Regeneración y saldos

Cuando el plan regenera asientos faltantes (compras/pagos o ventas/cobranzas), **también incluye el recálculo de saldos** del ejercicio en alcance (tablas de saldo de ejercicio y, si aplica, de período). En el diagnóstico verá impacto en `cont_asiento` y en las tablas de saldo.

---

## 3. Tablero de auditoría

**Menú:** Contabilidad → Tablero de auditoría.

### Para qué sirve

Correr los **diagnósticos de integridad** contable sobre la base legacy de la empresa de sesión y ver, por diagnóstico, si está OK (verde) o con diferencias (rojo).

### Cómo usarlo

1. Elija **Ejercicio** en la barra superior (obligatorio; búsqueda predictiva). La empresa es siempre la de su sesión (no se elige en pantalla). No hay filtro de período: los saldos se evalúan por ejercicio.
2. En la franja **Diagnósticos** (debajo de los filtros), pulse **Elegir** y marque cuáles ejecutar. **Por defecto no hay ninguno activo:** debe seleccionar **al menos uno**.
3. Pulse **Ejecutar**. Aparecerá el modal «Ejecutando auditoría».
4. Revise las tarjetas: cantidad de diferencias, severidad (Crítico / Alto / Medio).
5. Abra una tarjeta con diferencias para ver el detalle.
6. Si la tarjeta ofrece **Generar diagnóstico**, púlselo para armar el plan de corrección **de ese diagnóstico**.
7. Puede exportar **CSV** o **Excel** del resultado.

### Selección de diagnósticos

La selección ocupa una sola franja bajo los filtros. Muestra el contador «N de 18», hasta tres diagnósticos activos como chips (y «+K más» si hay más) o el aviso «Ninguno seleccionado».

Atajos de la franja:

- **Todos** / **Ninguno**: activan o vacían la lista completa.
- **Solo críticos**: deja activos únicamente los de severidad Crítico.
- **Elegir**: abre el panel de selección.

En el panel **Elegir**:

- **Filtrar diagnósticos…** acota la lista por título mientras escribe.
- La lista es scrolleable y está agrupada por severidad **Crítico / Alto / Medio**; cada subtítulo de sección muestra el avance (por ejemplo `2/6`) y, al pulsarlo, activa o desactiva todo el grupo.
- Cada fila tiene casilla, título y su badge de severidad; pulse la fila para activarla o desactivarla.
- Cierre con **Listo**, con `Esc` o haciendo clic fuera del panel.
- Con **cero diagnósticos** seleccionados, **Ejecutar**, **CSV** y **Excel** quedan deshabilitados (aviso «Elegí al menos un diagnóstico…»).
- La selección de esta franja define **qué se ejecuta**, no qué se corrige: el plan de corrección se genera después, diagnóstico por diagnóstico, desde su tarjeta.

### Comprobantes sin asiento (huérfanos)

Dos diagnósticos críticos listan comprobantes con `CodigoMovimiento` sin filas en `cont_asiento`:

| Diagnóstico | Tabla | Tipos | Contabilidad activa |
|-------------|-------|-------|---------------------|
| Compra/pago sin asiento | `cuentaproveedor` | FA, FC, OP | Sucursal con contabilidad (`sucursales.cont = Si`) |
| Venta/cobranza sin asiento | `cuentacliente` | FA, FB, FC, FE, FM, REC | Punto de venta con contabilidad (`punto_venta.cont = Si`) |

En el detalle de cada uno:

- Ve tipo, nro. de comprobante, fecha, importe, sucursal, P.V. y código de movimiento.
- Pulse **Generar diagnóstico** para armar el plan de regeneración (modal «Generando diagnóstico…»). El plan cubre **solo ese** diagnóstico.

### Avisos frecuentes

- «Ingresá empresa y ejercicio»: falta el ejercicio o no hay empresa en sesión.
- «Elegí al menos un diagnóstico para ejecutar la auditoría.»: no hay diagnósticos seleccionados.
- Tarjeta en ámbar con «Error: …»: falló ese diagnóstico (conexión o SQL); el resto puede haberse evaluado.
- Cero diferencias: el diagnóstico está OK para el alcance elegido; **no hay nada que abrir ni corregir**.
- «Sin corrección automática»: hay diferencias, pero ese diagnóstico no está en el motor de corrección; se resuelve manualmente en AdministraNET.

---

## 4. Diagnóstico de corrección (plan)

**Cómo llegar:** desde el tablero, con el botón **Generar diagnóstico** de una tarjeta con diferencias. La pantalla se abre con **ese** diagnóstico ya seleccionado.

### Para qué sirve

Generar un plan **sin escribir** en legacy: regeneración de asientos, reparación de anulaciones incompletas (compra/pago), ajustes de concepto, filas de saldo faltantes y **recompute de saldos**.

### Cómo usarlo

1. Llegue desde la tarjeta del tablero: el **ejercicio** y el **diagnóstico** vienen precargados. Puede cambiarlos desde la barra superior y la franja **Diagnósticos** si necesita otro alcance.
2. Pulse **Generar diagnóstico** (modal «Generando diagnóstico…»).
3. Revise:
   - **Guards** del plan (TTL, huella de configuración y de datos, **Id diagnóstico**).
   - **Asientos huérfanos a regenerar** (FA/FC/OP y FA/FB/…/REC según corresponda).
   - **Detalle de correcciones (muestra):** tabla con columnas Diagnóstico, Acción, Nro asiento, Fecha (dd/MM/yyyy), Cuenta, Debe, Haber, Descripción, Delta y Excluido (tocá una fila o el ícono para el detalle completo).
   - Impacto por tabla.
   - Anulaciones reparables / bloqueadas (si aplica).
4. Si el plan está vacío verá el aviso **«Plan vacío»** y **no** habrá botón de aplicar: el alcance no tiene correcciones automáticas (o ya están aplicadas).
5. Si hay ítems aplicables y tiene permiso de corregir, continúe a **Aplicar** (también en development para pruebas).

### Advertencia de performance

Si la política de alcance es **histórico**, el diagnóstico puede tardar mucho. Prefiera ejercicio seleccionado y ejecutar fuera del horario pico.

### Export

Desde el diagnóstico puede descargar el plan en **Excel** (mismas columnas contables: diagnóstico, asiento, fecha, cuenta, debe/haber, valores; sin JSON técnico).

---

## 5. Aplicar corrección

**Requisitos:**

- Permiso `contabilidad.auditoria.corregir` (válido en development y producción).
- Plan de diagnóstico vigente (dentro del TTL y con la misma huella de datos).
- Confirmación explícita en la UI (checkbox).

### Cómo usarlo

1. En el diagnóstico, revise el detalle de correcciones (ya formateado para decidir).
2. Pulse **Aplicar correcciones**: se abre un modal en la misma pantalla (no una página aparte).
3. Marque que entiende la escritura en la base contable y pulse **Aplicar definitivamente**. Verá el modal de espera «Aplicando corrección contable…».
4. Al terminar, Synap lo lleva a **Lotes** con el mensaje de éxito (anote el lote para eventual rollback).

### Qué hace el apply (orden)

1. Regenera asientos faltantes (compras/pagos y ventas/cobranzas).
2. Repara anulaciones incompletas de compra/pago (si el plan las incluye).
3. Ajusta conceptos de anulación incoherentes.
4. Inserta filas de saldo faltantes.
5. Actualiza saldos de ejercicio/período.

Cada apply crea **backup** previo de las tablas tocadas y deja log en `cont_audit_correccion_lote` / `cont_audit_correccion`.

---

## 6. Lotes aplicados, planes de diagnóstico y rollback

**Cómo llegar:** enlace **Lotes** en el tablero o en el diagnóstico.

### Para qué sirve

Consultar el **historial de planes de diagnóstico** generados (Postgres Synap) y los **lotes de corrección ya aplicados** (MySQL legacy). Desde un plan **vigente** puede **Abrir** el diagnóstico sin regenerarlo, o **Actualizar** para recalcular el plan con los mismos diagnósticos (mismo identificador). Si corresponde y tiene permiso, puede **revertir** un lote restaurando desde su backup.

### Planes de diagnóstico

La tabla superior lista los planes recientes de la empresa:

| Columna | Significado |
|---------|-------------|
| **Creado** | Fecha/hora del plan (dd/MM/yyyy). |
| **Estado** | **Vigente** (aún puede aplicarse) o **Aplicado** (ya se ejecutó la corrección). |
| **Ejercicio** | Ejercicio contable del alcance. |
| **Diagnósticos** | Checks incluidos en el plan. |
| **Ítems aplicables** | Cantidad de correcciones que el motor aplicaría. |
| **Expira** | Vencimiento del TTL del plan vigente. |
| **Acción** | **Abrir** (reabre sin recalcular) y **Actualizar** (recalcula el plan vigente, mismo identificador) solo en planes vigentes. |

#### Actualizar un plan vigente

1. En **Planes de diagnóstico**, pulse **Actualizar** en la fila del plan vigente, o abra el plan con **Abrir** y use el botón **Actualizar diagnóstico** en la pantalla de diagnóstico.
2. Synap muestra un aviso de espera mientras recalcula el plan (solo lectura en la base contable).
3. El plan conserva el mismo identificador y fecha de creación; se renueva la fecha de expiración (TTL) y se actualizan ítems, hashes y alcance según los datos actuales.
4. Si el plan ya venció, debe generar uno nuevo desde el tablero de auditoría.

Los planes vencidos o invalidados se purgan automáticamente al consultar esta pantalla.

### Lotes aplicados

La tabla inferior lista los lotes de corrección ya ejecutados en MySQL legacy:

| Columna | Significado |
|---------|-------------|
| **Lote** | Identificador del lote (`cont_audit_correccion_lote`). |
| **Fecha** | Fecha/hora de aplicación (dd/MM/yyyy HH:mm). |
| **Usuario** | Operador que ejecutó la corrección. |
| **Estado** | **Aplicado** o **Revertido**. |
| **Id diagnóstico** | Plan dry-run origen (truncado en pantalla). |
| **Filas log** | Cantidad de filas en `cont_audit_correccion`. |
| **Acción** | **Ver** (detalle), **Excel** (export) y, con permiso, **Revertir**. |

#### Ver detalle de un lote

1. En **Lotes aplicados**, pulse **Ver** (ícono o texto) en la fila del lote.
2. Se abre el detalle con resumen del lote y tabla de correcciones (diagnóstico, tabla, cambio a realizar, valor anterior corto, fecha).
3. Use **Excel** en el encabezado o el enlace **Excel** del listado para descargar el log completo (hojas **Resumen** y **Detalle**).

El Excel está pensado para análisis contable: columnas legibles (Diagnóstico, tipo de cambio, Nro asiento, Fecha, Cuenta, Debe/Haber en pesos argentinos, Descripción, Concepto, valores). En un **diagnóstico** las cabeceras van en potencial (**Cambios a realizar**, valor nuevo previsto); en un **lote aplicado**, en pasado (**Cambios aplicados**, valor aplicado). No incluye JSON técnico ni identificadores internos de check.

El detalle muestra hasta 500 filas en pantalla; si hay más, el aviso indica descargar Excel para el listado completo.

### Cómo revertir un lote

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

1. Genere el diagnóstico que incluya propuestas REI.
2. Abra la pantalla de aprobación REI del plan.
3. Apruebe o rechace cada caso (permiso `contabilidad.auditoria.rei`).
4. Solo entonces podrá aplicar en modo REI desde la pantalla de apply.

---

## 9. Permisos (resumen)

| Permiso | Qué habilita |
|---------|----------------|
| `contabilidad.auditoria.leer` | Tablero, diagnóstico de corrección, lotes y planes (consulta), ver configuración, **eliminar asientos (listar y vista previa)** |
| `contabilidad.auditoria.configurar` | Editar políticas |
| `contabilidad.auditoria.corregir` | Apply, rollback y **eliminación definitiva de asientos** (cualquier entorno) |
| `contabilidad.auditoria.rei` | Aprobar/rechazar REI |

Si no ve un botón o recibe error de permiso, solicite el alta al administrador Synap.

---

## 10. Problemas frecuentes

| Situación | Qué hacer |
|-----------|-----------|
| El tablero sigue en rojo después de un plan vacío | El plan solo cubre ciertos diagnósticos; vuelva a **Ejecutar** para refrescar. Un plan en Postgres no cambia el diagnóstico hasta el **apply**. |
| Veo hallazgos de otro ejercicio | Todos los diagnósticos respetan el ejercicio elegido en la barra; confirme el filtro antes de ejecutar. |
| «Ejecutar» está deshabilitado | Faltan ejercicio o diagnósticos: abra **Elegir** en la franja **Diagnósticos** y seleccione al menos uno. |
| No encuentro el botón para generar el plan en el encabezado | Ya no existe: se genera desde la tarjeta del diagnóstico, después de **Ejecutar**. |
| La tarjeta no tiene botón «Generar diagnóstico» | O tiene **0 diferencias** (nada que corregir), o dice **«Sin corrección automática»** (no está en el motor de corrección). |
| «Generar diagnóstico» tarda mucho y no veía aviso | Debe aparecer el modal de espera; si no, recargue la página (versión actualizada) y reintente. |
| Apply rechazado por permiso | Solicite `contabilidad.auditoria.corregir` al administrador. |
| Apply pide confirmar | Debe marcar el checkbox de confirmación antes de aplicar. |
| Huérfanos de venta = 0 pero había muchos | Las ventas usan gating por **punto de venta** (`cont = Si`), no por sucursal. |
| Regeneré asientos y cambiaron saldos | Es esperado: el plan encadena recálculo de saldos del ejercicio. |
| Rollback no disponible | Verifique permiso de corregir y que el lote tenga backups intactos. |

---

## 11. Resumen rápido por rol

**Consulta / auditoría diaria**

1. Tablero → ejercicio → seleccionar diagnósticos → Ejecutar.  
2. Revisar las tarjetas de diagnósticos críticos (huérfanos, saldos, anulaciones).  
3. Exportar si necesita llevar el detalle a Excel.

**Corrección de asientos faltantes**

1. Ejecutar el tablero → abrir la tarjeta de huérfanos → **Generar diagnóstico**.  
2. Revisar asientos a regenerar y impacto en saldos.  
3. Apply con confirmación (permiso de corregir).  
4. Guardar el id de lote; re-ejecutar auditoría para verificar verdes.

**Administración**

1. Configurar políticas (alcance, tolerancia, ejercicios cerrados).  
2. Revisar historial de políticas y lotes aplicados.  
3. Coordinar rollbacks solo cuando sea necesario.

---

---

## 12. Eliminar asientos (borrado físico)

Pantalla: **`/contabilidad/auditoria/asientos/`** (enlace **Eliminar asientos** en Tablero, Lotes o Diagnóstico).

Use este flujo solo cuando deba **quitar asientos completos** del diario (todos los renglones de un mismo número de asiento en el ejercicio). No sustituye al diagnóstico de corrección automática.

1. Elija el **ejercicio** (obligatorio).
2. Opcional: filtros por fecha, concepto, tipo de comprobante, CodigoMovimiento, anulado o texto en la descripción.
3. **Buscar** y marque los asientos con el checkbox (o **Seleccionar visibles** / **Importar nros**).
4. **Vista previa**: revisa renglones, cuentas impactadas y avisos.
5. **Eliminar definitivamente** (requiere `contabilidad.auditoria.corregir`): se crea backup, se borran los renglones y se recalculan saldos de cuentas/períodos afectados. El resultado queda en **Lotes** con `check_id` eliminación de asiento.

**Importante:** la operación es irreversible salvo **rollback** del lote si los backups siguen disponibles.

---

_Documentación técnica (equipo desarrollo): `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md`._
