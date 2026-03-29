# TPV en AdministraNET: autenticación del cajero/vendedor y operaciones de caja

Documento de análisis para integrar en Synap la **autenticación al iniciar la caja** y el flujo completo de **caja del TPV** (arqueo, cierre, tablas y permisos).

---

## 1. Autenticación del cajero/vendedor al ingresar al TPV

### 1.1 Dónde se dispara

- **Menú Principal** → Punto de Venta (o acceso directo `keyPuntoVenta`).
- **Principal.frm** (~líneas 5547–5592): antes de abrir el TPV se evalúa si debe pedir autenticación de vendedor.

### 1.2 Condiciones para pedir autenticación

Dos variables en `Principal` controlan el flujo (cargadas en **IngresoUsuario.frm** al login y en **Funciones.bas** según permisos del puesto):

| Variable | Origen | Efecto |
|----------|--------|--------|
| `apertura_cierre_caja_vendedor` | Permiso sistema (Case 178 en Funciones.bas) | Si = "Si", se exige lógica de apertura/cierre por vendedor. |
| `pedir_autenticacion_cierre_caja_vendedor` | Fijado a `"Si"` al final del login (IngresoUsuario ~2906); se pone en `"No"` solo después de autenticar correctamente al vendedor. | Si = "Si", al abrir TPV se muestra el diálogo de autenticación. |

Si **apertura_cierre_caja_vendedor = "Si"** y **pedir_autenticacion_cierre_caja_vendedor = "Si"**:

1. Se abre **Clave_Supervisor.frm** con:
   - `Motivo = "Autentica Vendedor Caja PV"`
   - Caption: "Autenticación de vendedor"
   - Solo campo **contraseña** (Usuario oculto).

### 1.3 Validación en Clave_Supervisor.frm

- **Tabla:** `viajantes` (vendedores/cajeros).
- **Consulta:**
  ```sql
  SELECT Nombre, CodViajante, clave_caja, anulado, logueado, detalle_logueo, ip_logueo
  FROM viajantes
  WHERE viajantes.clave_caja = '<password ingresada>' AND viajantes.anulado = 'No'
  ```
- **Condiciones para autorizar:**
  - Un solo registro (vendedor válido).
  - `logueado = 'No'` **o** (`logueado = 'Si'` y `ip_logueo = Principal.IP_Logueo_Usuario`) — evita doble uso en otra PC; permite reingreso desde la misma.

Opcional (si `caja_obliga_cierre_vendedor_tpv = "Si"`): se puede validar que el vendedor haya cerrado su caja antes de permitir otro login (código comentado en Clave_Supervisor).

### 1.4 Qué hace tras OK

- **UPDATE viajantes:**  
  `logueado = 'Si'`, `detalle_logueo = Principal.Datos_Logueo_Usuario`, `ip_logueo = Principal.IP_Logueo_Usuario`  
  para ese `CodViajante`.
- **Principal:**  
  `id_vendedor_usr = CodViajante`, `pedir_autenticacion_cierre_caja_vendedor = "No"`.
- Mensaje: "Vendedor: &lt;Nombre&gt; - Autorizado para trabajar en el punto de venta".
- **TPV.EstadoAntTipoComp = ""**, **TPV.Inicial**, **TPV.Show**.

Si el vendedor ya está logueado en otra estación: mensaje con `detalle_logueo` y no se abre el TPV.

### 1.5 Relación con el usuario de Windows

- El **usuario que abrió AdministraNET** ya está logueado en **IngresoUsuario** (tabla `usuarios`). Ese usuario tiene `codViajante` (vendedor por defecto).
- **Al abrir TPV con “apertura por vendedor”**, se pide la **clave de caja del vendedor** (`viajantes.clave_caja`), no el password del usuario. Así un mismo usuario de sistema puede “asumir” un cajero distinto ingresando su clave de caja.

---

## 2. Uso del vendedor en movimientos de caja y facturación

- **Principal.id_vendedor_usr** se usa en todos los movimientos de caja y en facturación TPV.
- En **caja**: cada fila de `caja` lleva `cod_vendedor = Principal.id_vendedor_usr` (CargaMovCaja, TPV, Caja.frm, ReciboCobro, etc.).
- En **stock/facturación**: TPV y otros formularios escriben `cod_vendedor` en `stock` y comprobantes cuando corresponde.

---

## 3. Operaciones de caja: cierre y arqueo

### 3.1 Tipos de cierre

| Motivo en CargaMovCaja | Quién | Destino del dinero |
|------------------------|--------|---------------------|
| **Cierre de Caja - Usuario de PV** | Cajero/vendedor cierra su caja de Punto de Venta | Caja destino (ej. caja deposito del usuario) |
| **Cierre de Caja - Usuario Supervisor** | Usuario supervisor (usuarios, id_puesto=1) | Caja acumulativa del supervisor (efectivo/cheque/tarjeta según tipo) |

### 3.2 Cómo se abre la pantalla de cierre

- **Desde Principal (menú Caja):**
  - **Caja Efectivo** → Caja.frm → menú “Movimiento de Caja” → **CargaMovCaja** con `Cierre_Caja_General = "No"`. El usuario elige motivo (Cierre Usuario PV o Supervisor).
  - **Cierre general** (keyCajaCierre) → si está activa la autenticación por vendedor, primero **Clave_Supervisor** con Motivo "Autentica Vendedor Caja Cierre General" → luego **Menu_Caja_Cierre_General_Codigo** → **CargaMovCaja** con `Cierre_Caja_General = "Si"`, motivo fijo y caja origen/destino prellenados.
- **Desde el TPV:** no hay botón directo “Cerrar caja” dentro de TPV.frm; el cierre se hace saliendo al menú Principal y entrando a Caja → Movimiento de Caja, o al Cierre general. Tras un **cierre de caja general** (y si corresponde), se llama **Cierra_Logueo_Vendedor** y se hace **Unload TPV**.

### 3.3 Flujo de “Cierre de Caja - Usuario de PV” (CargaMovCaja)

1. Usuario elige caja origen (PV del vendedor), caja destino, importe = saldo de la caja PV (o lo que se quiera cerrar).
2. Opcional: importe físico y diferencia (para Punto de Venta).
3. **INSERT en `caja`:**
   - `tipo = 'Cierre de Caja - Usuario de PV'`
   - `id_caja_abm_origen` = caja PV, `id_caja_abm_destino` = caja destino
   - `egreso` = importe, `ingreso` = 0, `Saldo` = saldo origen − egreso
   - `cod_vendedor = Principal.id_vendedor_usr`
   - `importe_fisico`, `importe_diferencia` si aplica
4. **UPDATE `caja_saldo`** de la caja origen (restar el egreso).
5. **Asignación de `id_cierre_caja`:**
   - Se obtiene un contador (codigo_movimiento) para el cierre.
   - **UPDATE caja** SET `id_cierre_caja` = contador WHERE `id_cierre_caja` IS NULL AND `id_caja_abm_origen` = caja PV.
   - Si hay caja destino (efectivo): también **UPDATE otro_egreso** con el mismo `id_cierre_caja` vía join con `caja`.
   - Para tarjeta/cheque: **UPDATE tc_comprobante** (y se guarda `Principal.id_cierre_tarjeta` o `id_cierre_cheque`).
6. **Movimiento en caja destino:** INSERT en `caja` con ingreso = mismo importe, para la caja acumulativa/deposito.

Al terminar el cierre general (y si aplica), se ejecuta **Cierra_Logueo_Vendedor** (UPDATE viajantes SET logueado='No', detalle_logueo=Null, ip_logueo=Null WHERE codviajante = Principal.id_vendedor_usr) y se cierra el TPV.

### 3.4 Arqueo de caja de efectivo

- **Objetivo:** Registrar el conteo físico del efectivo de uno o más cierres y marcar esos cierres como “arqueados”.
- **Acceso:** Principal → Caja → Arqueo (keyCajaArqueo). Si `visualiza_montos_caja = "No"`, antes se pide **Clave_Supervisor** con Motivo "Autentica Vendedor Arqueo" (misma validación por `viajantes.clave_caja`).

#### Arqueo “único” (por vendedor)

1. Tras autenticar vendedor, se abre **Caja_Arqueo.frm** con `Modo = "Arqueo unico"`, `id_vendedor` = CodViajante.
2. **Carga de cierres pendientes:**  
   Cierres del vendedor con `arqueo_cerrado = 'No'`, `tipo = 'Cierre de Caja - Usuario de PV'`, `egreso <> 0`, caja tipo Punto de Venta o Tarjeta.
3. El usuario elige número de cierre y carga **cantidades por billete/moneda** (20000, 10000, 2000, 1000, 500, 200, 100, 50, 20, 10, 5, 2, 1).
4. Se calcula **total_efectivo_fisico** y **total_diferencia** (físico − saldo sistema).
5. **INSERT en `caja_arqueo`:** codigo_movimiento, id_caja_abm_origen/destino, id_vendedor, montos y cantidades por denominación, fecha_hora, id_cierre_efectivo/id_cierre_tarjeta si aplica.
6. **UPDATE `caja`:** para los registros del cierre (tipo MCAJ, mismo nro_comprobante), se setea `importe_fisico`, `importe_diferencia`, `fecha_hora_act_arqueo`, **arqueo_cerrado = 'Si'**.
7. Reimpresión de arqueo (si está configurado). Se resetean `Principal.id_cierre_tarjeta` y `Principal.id_cierre_efectivo`.

### 3.5 Tablas implicadas

| Tabla | Uso principal |
|-------|----------------|
| **viajantes** | Cajeros/vendedores: clave_caja, logueado, detalle_logueo, ip_logueo. |
| **caja** | Movimientos: ingreso/egreso, tipo (incl. "Cierre de Caja - Usuario de PV"), id_cierre_caja, cod_vendedor, importe_fisico, importe_diferencia, arqueo_cerrado, fecha_hora_act_arqueo. |
| **caja_abm** | Maestro de cajas (Punto de Venta, Acumulativa, Tarjeta, etc.). |
| **caja_saldo** | Saldo actual por caja (y moneda). |
| **caja_arqueo** | Detalle del arqueo: denominaciones, total físico, codigo_movimiento (vinculado al cierre). |
| **usuarios** | id_caja, id_caja_deposito, id_caja_tarjeta, id_caja_cheque (cajas por defecto del usuario). |

---

## 4. Integración en Synap (TPV / self_checkout)

### 4.1 Autenticación del cajero al iniciar “caja”

- **Opción A – Mismo usuario Django:**  
  No pedir clave extra; el usuario que abre el TPV en Synap es el cajero. Se puede guardar `id_vendedor_usr` = `usuario.codViajante` (si existe en el perfil) y usarlo en `caja.cod_vendedor`.
- **Opción B – Clave de caja (paridad con VB6):**  
  - Tras login Synap, al abrir la vista TPV (o “Abrir caja”), si un permiso tipo `apertura_cierre_caja_vendedor` está activo, mostrar pantalla solo con campo **Clave de caja**.
  - Backend: validar contra `viajantes.clave_caja` (y `anulado = 'No'`). Comprobar `logueado = 'No'` o misma IP.
  - Actualizar `viajantes.logueado = 'Si'`, `detalle_logueo`, `ip_logueo`; guardar en sesión `id_vendedor_usr` = CodViajante.
  - Al “cerrar caja” / logout TPV, llamar equivalente a **Cierra_Logueo_Vendedor** (logueado = 'No', limpiar IP/detalle).

Recomendación: implementar **Opción B** si se quiere paridad con AdministraNET (varios cajeros por máquina y trazabilidad por vendedor).

### 4.2 APIs sugeridas

- **POST /api/self_checkout/tpv/auth-cashier/**  
  Body: `{ "clave_caja": "..." }`.  
  Respuesta: `{ "ok": true, "vendedor": { "CodViajante", "Nombre" } }` o error.  
  Efecto: validar en `viajantes`, actualizar logueado/detalle/IP, devolver vendedor y guardar en sesión.

- **POST /api/self_checkout/tpv/logout-cashier/**  
  Efecto: Cierra_Logueo_Vendedor para el `id_vendedor_usr` de la sesión.

- **GET /api/self_checkout/tpv/session/**  
  Devuelve si hay cajero logueado y su id/nombre (para mostrar en UI).

### 4.3 Caja: cierre y arqueo

- **Cierre de caja (Usuario de PV):**  
  - Endpoint que reciba caja origen (PV), caja destino, importe; opcional importe_fisico/diferencia.  
  - Replicar lógica de CargaMovCaja: INSERT en `caja`, UPDATE `caja_saldo`, asignación `id_cierre_caja`, movimiento en caja destino.  
  - Tras “cierre general”, llamar logout-cashier y cerrar sesión TPV en front.

- **Arqueo:**  
  - Listar cierres del vendedor con `arqueo_cerrado = 'No'`.  
  - Endpoint para enviar conteo por denominaciones; INSERT `caja_arqueo`, UPDATE `caja` (importe_fisico, importe_diferencia, arqueo_cerrado = 'Si', fecha_hora_act_arqueo).

- **Permisos:**  
  - Mapear en Synap permisos equivalentes a: apertura_cierre_caja_vendedor, oculta_boton_arqueo_cierre, visualiza_montos_caja (para exigir o no clave en arqueo).

### 4.4 Base de datos

- Las tablas `caja`, `caja_abm`, `caja_saldo`, `caja_arqueo`, `viajantes` están en MySQL (base empresa). El TPV en Synap ya escribe en `cuentacliente`, `stock`, etc.; hay que reutilizar la misma base para leer/escribir caja y viajantes.
- No es necesario duplicar tablas en PostgreSQL para este flujo; las APIs de Synap pueden usar el pool MySQL existente (reports/self_checkout) con la base empresa.

### 4.5 UI (resumen)

- Pantalla “Abrir caja” / “Ingresar al TPV”: si el permiso está activo, mostrar solo campo “Clave de caja” (y mensaje de error si ya está logueado en otra estación).
- Barra o menú TPV: mostrar “Cajero: &lt;Nombre&gt;” y botón “Cerrar caja / Salir”.
- Flujo “Cerrar caja”: pantalla o modal con caja origen/destino e importe (y opcional físico/diferencia), luego confirmación y cierre de sesión cajero.
- Arqueo: pantalla con lista de cierres pendientes de arqueo y formulario de conteo por billetes/monedas, luego guardar y marcar arqueo_cerrado.

---

## 5. Resumen

| Tema | AdministraNET (VB6) | Integración Synap |
|------|----------------------|-------------------|
| **Quién autentica al abrir TPV** | Clave de caja en `viajantes` (Clave_Supervisor, Motivo "Autentica Vendedor Caja PV"). | API auth-cashier contra `viajantes.clave_caja`; sesión con id_vendedor_usr. |
| **Control de sesión única** | Campo `logueado` e `ip_logueo` en viajantes. | Mismo criterio en validación y en logout-cashier. |
| **Cierre Usuario PV** | CargaMovCaja: INSERT caja, id_cierre_caja, movimiento destino, cod_vendedor. | Endpoint que replique lógica y escriba en MySQL. |
| **Cierre general** | CargaMovCaja con Cierre_Caja_General = "Si"; luego Cierra_Logueo_Vendedor y Unload TPV. | Mismo flujo vía API + logout-cashier y cierre de sesión TPV. |
| **Arqueo** | Caja_Arqueo: cierres con arqueo_cerrado='No', conteo por denominación, UPDATE caja + INSERT caja_arqueo. | Listado de cierres pendientes + endpoint de envío de arqueo. |
| **Permisos** | apertura_cierre_caja_vendedor, pedir_autenticacion_cierre_caja_vendedor, oculta_boton_arqueo_cierre, visualiza_montos_caja. | Mapear en permisos Synap y condicionar pantallas y endpoints. |

Este documento sirve como especificación para implementar en Synap la autenticación de cajero y el ciclo completo de caja (apertura, cierre, arqueo) compatibles con AdministraNET.
