# Propuesta: Factura electrónica (pyafipws) – Situación actual y mejoras

**Fecha:** 2025-01-31  
**Alcance:** Análisis de la implementación actual de factura electrónica AFIP en Synap (Self-Checkout) y propuesta de pasos siguientes. **No se realizan cambios de código en este documento.**

---

## 1. Resumen ejecutivo

La factura electrónica ya está **implementada** en el módulo **Self-Checkout**: se usa **pyafipws** (WSAA + WSFEv1) para obtener CAE o, en fallo de red, CAEA. Hoy la configuración es solo por variables de entorno; el flujo se dispara en la confirmación del carrito y hay un comando de reintentos para facturas fallidas. La propuesta recoge **gaps** y define **decisiones de diseño**:

- **Identificación del cliente:** Si no se identifica → Consumidor Final (FB). Para emitir FA debe existir **identificación por CUIT**, con **validación contra padrón AFIP desde el inicio** (obligatoria).
- **Configuración FE:** Debe hacerse mediante **UI/UX** (pantalla de configuración), con opción explícita **Homologación / Producción**. Homologación se usará para todas las pruebas; Producción solo cuando esté validado.

---

## 2. Documentación y código existentes

### 2.1 Documentación en el proyecto

| Ubicación | Contenido |
|-----------|-----------|
| **self_checkout/README.md** | Sección “FE (Factura Electrónica) con pyafipws”: variables de entorno, estados de factura (`pendiente`, `issued_cae`, `issued_caea_pending`, `sent`, `failed`), comando `self_checkout_retry_fe`, reglas de negocio (CAE vs CAEA). |
| **env.example** | Variables `AFIP_CERT_PATH`, `AFIP_KEY_PATH`, `AFIP_CUIT`, `AFIP_HOMO`, `AFIP_CACHE_DIR` con comentario de no loguear credenciales. |
| **docs/** | No existe un documento dedicado a “desarrollo/implementación AFIP”; la referencia está en el README del módulo y en comentarios del código. |

### 2.2 Referencias externas (pyafipws)

- **Sitio:** [pyafipws.com.ar](https://www.pyafipws.com.ar/)  
- **Manual:** [Manual PyAfipWs](https://www.sistemasagiles.com.ar/trac/wiki/ManualPyAfipWs) (Sistemas Ágiles).  
- **WSFEv1:** [Factura electrónica WSFEv1](https://www.pyafipws.com.ar/factura-electr%C3%B3nica/wsfev1).  
- **Ejemplos:** GitHub [reingart/pyafipws](https://github.com/reingart/pyafipws) (Python 2 y 3).  

El código actual usa **WSAA** (ticket de acceso) y **WSFEv1** (CAE / CAEA), alineado con esa documentación.

---

## 3. Implementación actual (resumen)

### 3.1 Componentes

| Componente | Ruta | Función |
|------------|------|--------|
| Configuración FE | `self_checkout/fe_config.py` | `get_fe_config()`, `is_fe_configured()`, `sanitize_for_log()`. Lee `AFIP_*` desde decouple, settings o `os.environ`. URLs WSAA/WSFE según `AFIP_HOMO`. |
| Servicio de factura | `self_checkout/services/invoice_service.py` | `InvoiceService`: `determinar_tipo_comprobante()`, `_obtener_datos_factura()`, `emitir_fe()`, `_intentar_caea()`, `guardar_invoice()`, `actualizar_invoice()`. |
| Uso en API | `self_checkout/api_views.py` | En `cart_confirm`: tras `ConfirmationService.confirmar()`, guarda registro en `self_checkout_invoice` y llama `emitir_fe()`; actualiza invoice con estado, CAE/vto_cae, fe_regimen, error_msg. |
| Reintentos | `self_checkout/management/commands/self_checkout_retry_fe.py` | Reintenta facturas con estado `issued_caea_pending` o `failed` (por base y límite; opción `--dry-run`). |
| Modelo de datos | `self_checkout/sql/001_self_checkout_tables.sql` | Tabla `self_checkout_invoice` (cart_id, codigo_movimiento, id_cuentacliente, nro_comprobante, tipo_comprobante, estado, cae, vto_cae, fe_regimen, request/response_payload, error_msg). |

### 3.2 Flujo de emisión

1. Usuario confirma carrito → `cart_confirm`.
2. `ConfirmationService.confirmar()` (transacción atómica):
   - codmov, talonarios, cuentacliente, stock, audit_log (sin commit).
   - Si FE está configurado: **antes del commit** se llama a `InvoiceService.emitir_fe()`:
     - Si FE no configurado → no se ejecuta FE; commit y venta confirmada.
     - Construye datos para WSFEv1 desde ítems del carrito (IVA por alícuota, totales).
     - WSAA: `Autenticar("wsfe", cert, key, wsdl, cache)`.
     - WSFEv1: `Conectar`, `CrearFactura`, `AgregarIva`, `CAESolicitar`.
     - Si resultado “A” y hay CAE → `issued_cae`; se actualiza `cuentacliente` con FE en la misma transacción; **commit**.
     - Si error de red → `_intentar_caea()` (CAEA solicitar/informar) → `issued_caea_pending` o `sent`; se actualiza `cuentacliente`; **commit**.
     - Si **no** se obtiene CAE ni CAEA (`failed`) → **rollback**; la venta **no** se finaliza (carrito sigue en pago_aprobado, no se reserva número ni se descuenta stock).
   - Si FE no está configurado: commit directo.
3. `cart_confirm`: `InvoiceService.guardar_invoice()` con estado/cae/vto_cae/fe_regimen devueltos por `confirmar()` (ya no se llama a `emitir_fe()` desde la API).

### 3.3 Seguridad

- Credenciales solo por entorno/settings; `sanitize_for_log()` evita loguear rutas de cert/key y CUIT.

---

## 4. Gaps y riesgos

### 4.1 Dependencia no declarada

- **Hecho:** En `invoice_service.py` se hace `from pyafipws.wsaa import WSAA` y `from pyafipws.wsfev1 import WSFEv1`, pero **pyafipws no figura en `requirements.txt`**.
- **Riesgo:** En entornos donde no se instale a mano, `ImportError` y respuesta “pyafipws no instalado” en FE.
- **Propuesta:** Añadir `pyafipws` a `requirements.txt` (con versión fijada si se conoce compatible). Documentar en README que FE requiere esa dependencia.

### 4.2 Tipo comprobante siempre FB

- **Hecho:** `determinar_tipo_comprobante()` hoy retorna siempre `"FB"` (salvo lógica por id_cliente == 1 o CUIT vacío). Hay un TODO para “consultar padrón AFIP / cliente.IDIVA para RI vs Monotributo”.
- **Riesgo:** Clientes que requieren FA no lo reciben; no se cumple norma fiscal.
- **Propuesta (acordada):** Si el cliente no se identifica → Consumidor Final (FB). Para emitir FA debe existir **identificación por CUIT** y **validación con padrón AFIP desde el inicio** (obligatoria). Ver sección 7.

### 4.3 Configuración AFIP solo por variables de entorno

- **Hecho:** La configuración FE (certificado, clave, CUIT, URLs) se lee solo de `.env` / settings; no hay pantalla de administración.
- **Riesgo:** Operadores deben editar archivos o variables; no hay selector Homologación vs Producción visible; errores de configuración más frecuentes.
- **Propuesta:** Configuración FE mediante **UI/UX**: pantalla de configuración (por base/empresa o global según diseño), con opción explícita **Homologación** / **Producción**. Homologación para todas las pruebas; Producción solo cuando esté validado. Ver sección 8.

### 4.4 Documentación de desarrollo/implementación

- **Hecho:** No hay un doc en `docs/` que describa flujo, decisiones y operación de FE.
- **Riesgo:** Onboarding y troubleshooting más lentos.
- **Propuesta:** Crear `docs/FACTURA_ELECTRONICA_AFIP.md` (o similar) con: flujo, configuración, estados, reintentos, errores frecuentes y enlaces a pyafipws/AFIP.

### 4.5 Pruebas automáticas

- **Hecho:** No hay tests específicos para `fe_config` ni `InvoiceService` (mocks de WSAA/WSFEv1).
- **Riesgo:** Regresiones al tocar FE o reintentos.
- **Propuesta:** Añadir tests unitarios con mocks de pyafipws (y opcional integración en homologación, fuera de CI estándar).

### 4.6 Reintentos y monitoreo

- **Hecho:** Reintentos solo vía comando manual `self_checkout_retry_fe`.
- **Riesgo:** Facturas `failed` o `issued_caea_pending` pueden quedar sin reintento si no se ejecuta el comando.
- **Propuesta:** Evaluar tarea programada (cron/celery) para reintentos y alertas (ej. cantidad de `failed` por día).

---

## 5. Propuesta de pasos (orden sugerido)

Sin implementar todavía, se sugiere este orden:

1. **Dependencia:** Incluir `pyafipws` en `requirements.txt` y mencionarlo en `self_checkout/README.md`.  
2. **Configuración FE por UI/UX:** Pantalla de configuración FE (cert, clave, CUIT, modo Homologación/Producción). Homologación para todas las pruebas; Producción solo cuando esté validado. Ver sección 8.  
3. **Identificación cliente y FA/FB:** Si el cliente no se identifica → Consumidor Final (FB). Opción de identificación por CUIT para emitir FA; **validación con padrón AFIP desde el inicio** (obligatoria). Ver sección 7.  
4. **Documentación:** Añadir `docs/FACTURA_ELECTRONICA_AFIP.md` con flujo, configuración, estados, reintentos y referencias.  
5. **Tests:** Tests unitarios para `fe_config` e `InvoiceService` (mocks de WSAA/WSFEv1).  
6. **Reintentos/operación:** Cron o tarea programada para `self_checkout_retry_fe` y, si aplica, monitoreo de facturas fallidas.  
7. **Multi-CUIT (opcional):** Solo si el negocio lo exige; diseño de configuración por base/kiosco y refactor de `fe_config`/`InvoiceService`.

---

## 6. Referencias rápidas en el repo

| Tema | Archivo / Ubicación |
|------|----------------------|
| Config FE | `self_checkout/fe_config.py` |
| Emisión CAE/CAEA | `self_checkout/services/invoice_service.py` |
| Integración en confirmación | `self_checkout/api_views.py` → `cart_confirm` |
| Reintentos | `self_checkout/management/commands/self_checkout_retry_fe.py` |
| Tabla facturas | `self_checkout/sql/001_self_checkout_tables.sql` → `self_checkout_invoice` |
| Variables AFIP | `env.example` (AFIP_*) |
| Descripción alta nivel | `self_checkout/README.md` (sección FE) |
| Propuesta: Config FE por UI/UX | Sección 8 de este documento |
| Propuesta: Identificación cliente + padrón AFIP | Sección 7 de este documento |

---

## 7. Identificación del cliente para FA / FB (condición IVA)

**Regla acordada:** Si el cliente **no se identifica** → **Consumidor Final** (FB). Para emitir **FA** debe existir **identificación por CUIT**, con **validación contra padrón AFIP desde el inicio** (obligatoria).

### 7.1 Principio

- **Cliente no identificado** → siempre **FB** (Consumidor Final). No se requiere CUIT; el documento en el comprobante puede ser 0 o el ingresado por el usuario en el kiosco (solo para identificación, sin exigir condición fiscal).
- **Cliente identificado por CUIT** → se debe **validar contra padrón AFIP** antes de decidir FA o FB. La condición fiscal que define el tipo de comprobante es la que devuelve AFIP (no solo la que pueda existir en administraNET).

### 7.2 Validación con padrón AFIP (obligatoria desde el inicio)

- Para emitir **FA** es obligatorio que el comprador esté identificado por **CUIT** y que su condición fiscal sea la que corresponde a Factura A según AFIP.
- La **validación con padrón AFIP** (WS Padrón A5 o equivalente) debe estar implementada **desde el inicio**: antes de autorizar FA se consulta el CUIT en AFIP y se obtiene la categoría/condición fiscal. Solo si AFIP indica que corresponde Factura A (ej. RI, Monotributo según normativa) se emite FA; en caso contrario se emite FB.
- Esto evita discrepancias con el padrón y cumple con la obligación de verificar la condición del comprador en la fuente oficial.

### 7.3 Opción de identificación por CUIT en el flujo

- En el kiosco / flujo de confirmación debe existir una **opción de identificación por CUIT**: el usuario puede ingresar su CUIT (con o sin guiones) para solicitar factura con ese comprador.
- Si **no ingresa CUIT** (o no se identifica de otro modo) → **Consumidor Final** → **FB**.
- Si **ingresa CUIT**:
  1. Validar formato (11 dígitos).
  2. **Consultar padrón AFIP** con ese CUIT.
  3. Según la condición devuelta por AFIP: si corresponde FA → emitir **FA**; si no → emitir **FB** (y opcionalmente informar al usuario).
- Opcionalmente se puede seguir usando `id_cliente` del maestro de administraNET cuando el cliente ya esté cargado: si `id_cliente > 1` y el cliente tiene CUIT e IDIVA en `cliente`, se puede usar ese CUIT para la consulta al padrón y cruzar con el resultado AFIP; la decisión FA/FB debe basarse en el resultado del padrón, no solo en IDIVA local.

### 7.4 Resumen

| Situación | Acción | Comprobante |
|-----------|--------|-------------|
| Cliente no identificado (sin CUIT) | Consumidor Final | **FB** |
| Cliente identificado por CUIT | Consultar padrón AFIP; si AFIP indica condición que corresponde a Factura A → FA | **FA** o **FB** según padrón |
| CUIT inválido o no encontrado en padrón | No emitir FA; emitir FB o informar error según diseño | **FB** o bloqueo |

La **validación con padrón AFIP** es requisito desde el inicio para todo flujo que pueda emitir FA.

---

## 8. Configuración de Factura Electrónica por UI/UX

La configuración de Factura Electrónica debe realizarse mediante **interfaz de usuario** (UI/UX), no solo por variables de entorno. Debe incluir la opción explícita **Homologación / Producción**; **Homologación** se usará para todas las pruebas.

### 8.1 Requisitos de la pantalla de configuración

- **Pantalla de configuración FE** accesible desde el menú o módulo correspondiente (por ejemplo dentro de Self-Checkout o un módulo “Facturación AFIP”), con permisos adecuados.
- **Datos configurables vía UI** (persistidos en base o en configuración por empresa):
  - Ruta o carga de **certificado** AFIP (archivo .crt / .pem).
  - Ruta o carga de **clave privada** (archivo .key / .pem).
  - **CUIT** del contribuyente (11 dígitos).
  - **Modo:** **Homologación** o **Producción** (selector explícito, no solo variable oculta).
- **Homologación:** utiliza entornos de prueba de AFIP (wsaahomo, wswhomo). Sirve para **todas las pruebas** (desarrollo, QA, integración). No se envían comprobantes reales.
- **Producción:** utiliza entornos reales de AFIP. Solo debe activarse cuando la configuración y el flujo estén validados en Homologación.
- Opcional: directorio de caché (ej. `/tmp/pyafipws_cache`) configurable o por defecto.
- **Seguridad:** no mostrar ni loguear la clave privada ni el CUIT completo en logs; validar permisos para acceder a la pantalla.

### 8.2 Comportamiento según modo

| Modo | Uso | URLs AFIP (ejemplo) |
|------|-----|----------------------|
| **Homologación** | Todas las pruebas (desarrollo, QA, integración). | WSAA: wsaahomo.afip.gov.ar; WSFEv1: wswhomo.afip.gov.ar |
| **Producción** | Solo cuando esté validado. | WSAA: wsaa.afip.gov.ar; WSFEv1: servicios1.afip.gov.ar |

La aplicación debe leer el modo seleccionado en la UI y usar las URLs y WSDL correspondientes (igual que hoy con `AFIP_HOMO`, pero con el valor fijado desde la configuración guardada en UI).

### 8.3 Persistencia y compatibilidad

- La configuración guardada desde la UI puede persistirse en base de datos (tabla de configuración por empresa/base) o en un modelo Django si se prefiere. Las variables de entorno pueden quedar como fallback o solo para despliegues que no usen UI.
- Al cargar la pantalla, mostrar el modo actual (Homologación/Producción) y advertir claramente cuando esté en Producción para evitar pruebas accidentales en ambiente real.

---

## 9. administraNET (VB6): certificados y proceso de factura electrónica

Esta sección resume cómo el proyecto **administraNET** (VB6) busca, administra y usa los certificados para factura electrónica, y cuál es el flujo al emitir la factura. Sirve de referencia para alinear Synap/fe_afip con el comportamiento existente.

### 9.1 Dónde se guardan las rutas del certificado

- **Tabla:** `punto_venta` (MySQL administraNET).
- **Campos:**
  - `ruta_certificado`: ruta (carpeta) donde están el certificado y la clave, típicamente en red o servidor (ej. `\\servidor\Certificado FE` o ruta UNC).
  - `ruta_certificado_local`: ruta local en la PC del usuario (ej. `C:\administraNET\Certificado FE`), usada cuando `certificado_afip_local = "Si"`.
- **Regla de uso:** Si en la configuración global está `Principal.certificado_afip_local = "Si"`, se usa `ruta_certificado_local` del punto de venta; si no, se usa `ruta_certificado`.
- **Archivos esperados en esa carpeta:** siempre los mismos nombres:
  - `certificado.crt` (certificado AFIP)
  - `clave.key` (clave privada)
- Es decir: **una carpeta por punto de venta**; dentro, `certificado.crt` y `clave.key`.

### 9.2 Cómo se administran los certificados (alta/edición de PV)

- **Formulario:** `CargaPV.frm` (Carga / Edición de Punto de Venta).
- **Campos en el formulario:**
  - **Ruta certificado:** texto + botón **“Carga Certificado”** (o similar).
  - **Ruta certificado local:** texto + botón **“Carga Certificado Local”**.
- **Botón “Carga Certificado”:** abre el **explorador de carpetas** de Windows (`SHBrowseForFolder` con `BIF_RETURNONLYFSDIRS`). El usuario elige la **carpeta** donde están `certificado.crt` y `clave.key`; la ruta seleccionada se escribe en el campo “Ruta certificado”.
- **Botón “Carga Certificado Local”:** igual, pero para la ruta local; el resultado se guarda en “Ruta certificado local”.
- Al guardar el punto de venta (alta o modificación), se persisten en `punto_venta` los valores de `ruta_certificado` y `ruta_certificado_local`.

### 9.3 Cómo se obtiene la ruta al abrir factura/TPV

- Al abrir **FacturaA**, **FacturaB**, **TPV**, **NotaCred**, etc., se ejecuta una rutina tipo **Verifica_pv_electronico** (o equivalente) que:
  1. Lee el punto de venta seleccionado (o el del usuario) desde `punto_venta`.
  2. Si el PV tiene `fe_regimen = "Si"` (facturación electrónica):
     - Toma `id_punto_venta`, `nro_punto_venta`, `fe_regimen_tipo` (CAE/CAEA).
     - Si `Principal.certificado_afip_local = "Si"` → `Principal.ruta_certificado = rs_pv_elect.Fields!ruta_certificado_local`.
     - Si no → `Principal.ruta_certificado = rs_pv_elect.Fields!ruta_certificado`.
  3. El resto del flujo FE usa siempre `Principal.ruta_certificado + "\certificado.crt"` y `Principal.ruta_certificado + "\clave.key"`.
- **Función auxiliar:** `Obtener_Ruta_Certificado_AFIP(id_pv)` en `Funciones.bas` devuelve `ruta_certificado` del `punto_venta` para un `id_pv` dado.

### 9.4 Verificación de vencimiento del certificado

- **Formulario:** `adm_felectronicas.frm` (administración de facturas electrónicas).
- **Menú/acción:** “Verificación de vencimiento de certificado”.
- **Proceso:** Se instancia `FEAFIPLib.Certificado`, se llama `CargarInformacionCertificado(ruta_certificado + "\certificado.crt", ruta_certificado + "\clave.key")`. Si responde bien, se muestra la fecha de vencimiento (`IC_FechaVencimiento`) en un mensaje al usuario.

### 9.5 URLs y CUIT de AFIP (Principal)

- Las URLs de AFIP y el CUIT no se guardan en `punto_venta`; están en el **módulo Principal** (variables globales de la aplicación):
  - `Principal.fe_url_login`: URL de login WSAA (ej. homologación vs producción).
  - `Principal.fe_url_acceso_servidor`: URL del servidor WSFEv1.
  - `Principal.fe_CUIT_empresa`: CUIT del contribuyente para FE.
  - `Principal.certificado_afip_local`: "Si" / "No" para elegir ruta local vs red.
- En escenarios con **segunda empresa** (multi-CUIT), el CUIT puede venir de `Obtener_CUIT_2da_Empresa(id_pv_electronico)` según el punto de venta.

### 9.6 Proceso al emitir la factura electrónica (FE con CAE)

Flujo resumido en **FacturaA.frm** (y análogo en FacturaB, TPV, Notas de Crédito/Débito):

1. **Condiciones:** PV electrónico (`pv_electronico = "Si"`), factura por sistema, régimen CAE (`fe_regimen_tipo = "CAE"`).
2. **URLs y cliente WSFE:** Se toman `URLWSAA = Principal.fe_url_login` y `URLWSW = Principal.fe_url_acceso_servidor`. Se crea `FEAFIPLib.wsfev1`, se asigna `CUIT` (empresa o 2ª empresa) y `URL`.
3. **Login WSAA:** `wsfev1.login(Principal.ruta_certificado + "\certificado.crt", Principal.ruta_certificado + "\clave.key", URLWSAA)`. Si falla, se informa “servicio ARCA caído” y no se autoriza.
4. **Último número informado a AFIP:** `wsfev1.RecuperaLastCMP(PtoVta, TipoComp, Nro_elect)`. Se obtiene el último comprobante emitido para ese PV y tipo (FA, FM, etc.). Se valida que coincida con el numerador local (talonarios); si no coincide, se avisa y no se continúa.
5. **Numeración:** Se asigna `Nro_elect + 1` como próximo número, se actualiza el talonario en base (tabla `talonarios`).
6. **Armado del comprobante en memoria:**  
   `wsfev1.Reset`, luego:
   - `AgregaFactura` (concepto, tipo doc receptor, CUIT receptor, número, fechas, importes, moneda, condición IVA receptor, etc.).
   - Opcionales (ej. factura de crédito: CBU, ley 27.440).
   - Por cada alícuota de IVA: `AgregaIVA(codigo_afip, neto, iva)`.
   - Tributos: impuesto interno, percepciones (si aplica) con `AgregaTributo`.
7. **Autorización (solicitud de CAE):** `wsfev1.Autorizar(PtoVta, TipoComp)`. Si la respuesta es correcta:
   - Se lee `CAE` y fecha de vencimiento del CAE con `SFCAE(0)`, `SFVencimiento(0)` (o `AutorizarRespuesta`).
   - Se actualiza la tabla `cuentacliente` (registro del comprobante): `fe_cae`, `fe_vto_cae`, `fe_comp`, `fe_transmitido`, `fe_regimen_tipo`.
   - Se genera el código QR / código de barras del CAE para impresión o PDF.
8. **Si Autorizar falla:** Se muestra el mensaje de error/observación de AFIP (ej. rechazo por condición fiscal, ley 27.440, etc.) y no se actualiza el comprobante con CAE.

### 9.7 Resumen para Synap / fe_afip

| Aspecto | administraNET (VB6) | Synap / fe_afip (referencia) |
|--------|----------------------|------------------------------|
| Dónde se guarda la ruta del certificado | Por **punto de venta**: `punto_venta.ruta_certificado`, `ruta_certificado_local` | Por **empresa/base**: `AFIPConfig` (cert_path, key_path); opcionalmente por kiosco/PV si se extiende. |
| Nombres de archivos | Siempre `certificado.crt` y `clave.key` en una carpeta | Configurables en UI (ruta completa a .crt y .key). |
| Selección de carpeta/archivo | Explorador de **carpetas** (SHBrowseForFolder) en CargaPV | Explorador de **archivos/directorios** en config FE (fe_afip), vía API `browse/` y modal en el formulario. |
| Login WSAA | `wsfev1.login(cert_path, key_path, URLWSAA)` (FEAFIPLib) | pyafipws: WSAA + WSFEv1; cert/key/CUIT desde `fe_config` o `AFIPConfig`. |
| Flujo de emisión | RecuperaLastCMP → validar numeración → AgregaFactura/IVA/Tributo → Autorizar → guardar CAE en cuentacliente | Similar: último número (talonarios), CrearFactura/AgregarIva, CAESolicitar, guardar en `self_checkout_invoice` y cuentacliente. |
| Verificación de vencimiento | FEAFIPLib.Certificado.CargarInformacionCertificado → mostrar fecha vencimiento | Opcional en fe_afip: leer cert y mostrar vencimiento en UI o tarea. |

Tener en cuenta que en administraNET la configuración de **URLs y CUIT** es global (Principal), mientras que la **ruta del certificado** es por punto de venta; en Synap/fe_afip hoy todo es por base/empresa (AFIPConfig), y el kiosco solo asocia un `id_punto_venta` para numeración y contexto.

---

## 10. Guardar factura y CAE/CAEA como administraNET; CAEA cuando AFIP falla

### 10.1 Mismo proceso de guardado que administraNET

En Synap/self_checkout se sigue el mismo criterio que en administraNET para persistir el resultado de la factura electrónica:

1. **No finalizar venta sin CAE/CAEA:** Si FE está configurado, la emisión (`emitir_fe`) se ejecuta **dentro** de la transacción de confirmación, **antes** del `commit`. Si no se obtiene CAE ni CAEA (`estado_fe == 'failed'`), se hace **rollback** de toda la transacción: no se confirma el carrito, no se reserva número de comprobante ni se descuenta stock. La venta solo se finaliza cuando hay CAE o CAEA (o cuando FE no está configurado).
2. **self_checkout_invoice:** se guarda siempre (tras confirmar): `cart_id`, `codigo_movimiento`, `id_cuentacliente`, `nro_comprobante`, `tipo_comprobante`, estado según resultado FE. Los datos de CAE/CAEA ya vienen del resultado de `confirmar()` (FE ejecutado dentro del servicio).
3. **cuentacliente:** tras obtener CAE o CAEA dentro de `confirmar()`, se actualiza el registro del comprobante (el mismo que inserta `ConfirmationService`) con:
   - **fe_cae:** número de CAE o de CAEA (mismo campo).
   - **fe_vto_cae:** fecha de vencimiento del CAE (CAEA no tiene vto en el mismo formato; puede ir NULL).
   - **fe_comp:** `'Si'` cuando hay comprobante electrónico (tenemos CAE o CAEA).
   - **fe_transmitido:** `'Si'` solo cuando el comprobante fue efectivamente transmitido y aceptado por AFIP (CAE autorizado o CAEA informado OK). Si se obtuvo CAEA pero aún no se pudo informar → `'No'` hasta el reintento.
   - **fe_regimen_tipo:** `'CAE'` o `'CAEA'` según el régimen con el que se obtuvo la autorización.

Esa actualización se hace **dentro de** `ConfirmationService.confirmar()` (mismo cursor, antes del commit) cuando FE devuelve CAE o CAEA; y en el comando `self_checkout_retry_fe` cuando un reintento tiene éxito, mediante `InvoiceService.actualizar_cuentacliente_fe()`. Solo se aplica cuando el estado FE es `issued_cae`, `sent` o `issued_caea_pending`.

### 10.2 ¿Qué pasa con CAEA cuando AFIP falla?

Cuando **AFIP falla** (servicio caído, timeout, error de red), el flujo es:

1. **Primero se intenta CAE** (autorización comprobante por comprobante): `CAESolicitar()`. Si AFIP responde OK → se guarda CAE, se actualiza `self_checkout_invoice` y **cuentacliente** (fe_cae, fe_vto_cae, fe_comp = 'Si', fe_transmitido = 'Si', fe_regimen_tipo = 'CAE').
2. **Si CAE falla por error de red/connectividad** (`_es_error_red`): se entra al **fallback CAEA**:
   - Se solicita un **CAEA** para el período (mes actual): `CAEAConsultar` o `CAEASolicitar`.
   - Con ese CAEA se arma el comprobante y se envía **CAEARegInformativo** (informe a AFIP).
   - **Si CAEARegInformativo responde OK** → estado `sent`, fe_regimen = 'CAEA'. Se actualiza cuentacliente con fe_cae = valor CAEA, fe_comp = 'Si', fe_transmitido = 'Si', fe_regimen_tipo = 'CAEA'.
   - **Si CAEARegInformativo falla** (ej. AFIP sigue caído) → estado `issued_caea_pending`. Se guarda el número de CAEA en `cae` y fe_regimen = 'CAEA'; se actualiza cuentacliente con fe_cae = CAEA, fe_comp = 'Si', fe_transmitido = **'No'** (aún no informado). Un **reintento posterior** (comando `self_checkout_retry_fe` o tarea programada) vuelve a llamar a `emitir_fe()`; si en el reintento se logra informar el comprobante con ese CAEA, se pasa a `sent` y se actualiza fe_transmitido = 'Si'.

Resumen:

| Situación | Estado FE | cuentacliente fe_comp / fe_transmitido | Acción posterior |
|-----------|-----------|----------------------------------------|------------------|
| CAE OK | `issued_cae` | Si / Si | Ninguna |
| AFIP caído → CAEA obtenido e informado OK | `sent` | Si / Si | Ninguna |
| AFIP caído → CAEA obtenido pero informar falla | `issued_caea_pending` | Si / **No** | Reintento (`self_checkout_retry_fe` o cron) para volver a informar con el mismo CAEA |
| FE falla sin CAE ni CAEA | `failed` | No se actualiza cuentacliente | Reintento puede intentar CAE de nuevo |

Así se mantiene el mismo criterio que administraNET: la factura y el CAE/CAEA se reflejan en **cuentacliente** (fe_cae, fe_vto_cae, fe_comp, fe_transmitido, fe_regimen_tipo), y cuando AFIP falla se usa CAEA como respaldo, guardando el número y dejando pendiente el informe hasta que el reintento lo complete.

---

*Documento de propuesta; no implica cambios en el código hasta que se decida su ejecución.*
