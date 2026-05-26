# Certificados AFIP (ARCA) para Factura Electrónica

Flujo desde Synap para obtener e importar el certificado digital usado en Facturación Electrónica (WSAA/WSFEv1).

## Si ya tenés certificados válidos de AFIP

Si la empresa **ya tiene** el certificado (.crt) y la clave privada (.key) obtenidos antes por AFIP (por este u otro medio), **no hace falta usar el asistente Certificados ARCA**. En ese caso:

1. Ir a **Configuración AFIP** (Facturación Electrónica).
2. Clic en **Configurar AFIP** (si no hay configuración) o **Editar configuración** (si ya existe).
3. Completar **Ruta certificado** y **Ruta clave privada** con las rutas absolutas en el servidor donde están el `.crt` y el `.key` (podés usar *Examinar* si el servidor lo permite).
4. Indicar **CUIT** (11 dígitos) y **Modo Homologación** o **Producción** según corresponda.
5. Guardar.

El asistente **Certificados ARCA** sirve solo cuando querés **generar un CSR nuevo**, subirlo a AFIP, descargar el .crt e importarlo en Synap desde cero.

## Relación CUIT y base_empresa

- El certificado se solicita con el **CUIT de la empresa** obtenido desde **administraNET** (tabla `DatosEmpresa` de la base de la empresa). En el paso 1 del asistente el CUIT se muestra en **solo lectura** para evitar errores: no es editable.
- Si en administraNET la empresa no tiene CUIT configurado o no tiene 11 dígitos válidos, el asistente muestra un mensaje y no permite generar el CSR hasta que se configure el CUIT en administraNET (Datos de empresa).
- El vínculo es: sesión → `base_empresa` → conexión MySQL a esa base → `DatosEmpresa.CUIT`.

## Un certificado por CUIT

- **No** se puede usar un certificado de homologación (ni de producción) para **otro CUIT**. AFIP emite el certificado para el CUIT que figura en el CSR (CN = CUIT). Un certificado emitido para un CUIT no puede usarse para firmar solicitudes con otro CUIT.

## Homologación vs Producción

- **Al generar el CSR** no se diferencia homologación/producción: el request es solo local (clave + CSR). No se envía nada a AFIP en ese paso.
- **Al importar el .crt** el usuario debe indicar si el certificado es para **Homologación** o **Producción**. Ese valor se guarda en `AFIPConfig.modo_homologacion` y define qué servicios AFIP usa (wsaahomo/wsfehomo vs producción).
- En AFIP suelen existir certificados distintos según el ambiente (homologación para pruebas, producción para facturación real). El modo elegido al importar debe coincidir con el ambiente en el que se solicitó el certificado en ARCA.

### Cómo ver qué tipo está configurado

- **En Synap:** En **FE-AFIP → Configuración AFIP** (lista de configuraciones) cada fila muestra un badge **Homologación** (ámbar) o **Producción** (verde). En **Editar configuración** el checkbox **Modo Homologación** indica si está en homologación o producción.
- **En AFIP ARCA:** La pantalla "Administración de Certificados Digitales" no suele indicar en la lista si cada certificado es de homologación o producción. Se sabe por el ambiente en el que lo agregaste: si entraste a ARCA en modo prueba/homologación, el certificado que descargaste es de homologación; si es el ambiente real, es de producción. Lo importante es que en Synap el **Modo Homologación** coincida con el ambiente para el que se emitió ese certificado en AFIP.

## Quién puede usarlo

Solo **administradores o supervisores**, o usuarios con permiso `fe_afip.change_afipconfig` o `fe_afip.add_afipconfig`.

## Flujo en la UI

1. **Configuración AFIP** → botón **Certificados ARCA**.
2. **Paso 1 – Generar CSR**
   - Ingresar CUIT (11 dígitos) y alias (ej. FACTELEC).
   - Clic en **Generar CSR**. Synap genera clave privada y CSR (PKCS#10) y guarda la clave de forma temporal.
3. **Paso 2 – AFIP**
   - Descargar el archivo CSR o copiar el contenido.
   - En AFIP: **Clave Fiscal** → **Administración de Certificados Digitales** (ARCA) → **Agregar alias**.
   - Subir el CSR (PKCS#10), indicar el alias, y descargar el certificado (.crt).
4. **Paso 2 – Synap**
   - En la misma pantalla, subir el archivo .crt descargado e indicar si el certificado es para **Homologación** o **Producción**.
   - **Importar certificado**: Synap guarda certificado y clave en el directorio configurado, actualiza (o crea) la configuración AFIP de la empresa y deja configurado el modo Homologación/Producción según lo elegido.

## Configuración opcional

- **FE_AFIP_CERT_STORAGE_DIR**: directorio donde se guardan `certificado.crt` y `clave.key` por empresa (subcarpeta por `base_empresa`). Por defecto: `MEDIA_ROOT/fe_afip/certs/`.
- **FE_AFIP_PENDING_DIR**: directorio de claves pendientes hasta que se suba el .crt. Por defecto: `MEDIA_ROOT/fe_afip/pending/`.

En producción puede definirse, por ejemplo, `FE_AFIP_CERT_STORAGE_DIR=/var/synap/fe_afip_certs` para mantener certificados fuera de `media`.

## Seguridad

- La clave privada se escribe en disco con permisos 0o600; se elimina del directorio “pending” después de importar el certificado.
- No se guarda CSR ni clave en sesión; solo un token que referencia el archivo de clave pendiente.
- Solo usuarios con permiso de administrar configuración AFIP pueden acceder al asistente.

## Errores frecuentes

### "Computador no autorizado a acceder al servicio" (coe.notAuthorized)

AFIP rechaza la conexión porque **el equipo (servidor/IP) desde el que Synap se conecta no está autorizado** para usar el servicio en cuestión.

**Servicios que Synap usa y que requieren autorización de IP en AFIP:**

- **Facturación Electrónica (WSFE)** – emisión de comprobantes, CAE/CAEA.
- **Padrón A5 (o Padrón A4)** – consulta de CUIT para razón social y condición fiscal (p. ej. en el TPV al buscar cliente por CUIT). En **homologación** el servicio también debe estar dado de alta y la IP autorizada.

**Qué hacer:**

1. Entrá a **AFIP** con Clave Fiscal (el CUIT de la empresa).
2. En el **mismo ambiente** que usás en Synap (Homologación o Producción), ir a **Servicios web** (o “Administración de relaciones”).
3. Para **Facturación Electrónica**: buscar **Autorizar equipos** / **Computadores autorizados** (puede estar en Administración de Puntos de Venta o en la configuración del servicio) y agregar la IP.
4. Para **consultas al padrón (CUIT en TPV)**: dar de alta el servicio **Padrón A5** (o Padrón A4) y en la configuración de ese servicio **agregar la IP pública** desde la que se conecta Synap.
5. **IP a cargar**: si Synap corre en tu PC o Docker local, es la IP pública de tu conexión (p. ej. la que muestra [cual-es-mi-ip.net](https://www.cual-es-mi-ip.net)); si corre en un servidor, la IP pública de ese servidor.
6. Guardar y esperar unos minutos si AFIP indica propagación.

Sin este paso, AFIP rechaza las solicitudes (WSAA, Padrón, etc.) aunque el certificado sea válido.

### "Certificado no emitido por AC de confianza" (cms.cert.untrusted)

AFIP rechaza el certificado porque **no fue emitido por la AC (Autoridad Certificante) que AFIP confía** en ese ambiente.

**Qué hacer:**

1. **Homologación:** El certificado debe haberse solicitado y descargado desde AFIP ARCA para **Homologación**. No sirve un certificado de producción en homologación ni uno autofirmado.
2. **Producción:** El certificado debe ser el emitido por AFIP ARCA para **Producción**.
3. En Synap, en **Configuración AFIP (FE-AFIP)**, verificá que:
   - **Modo Homologación** esté marcado si estás probando con wsaahomo/wsfehomo.
   - Las rutas de **certificado** y **clave privada** apunten a los archivos `.crt` y `.key` obtenidos de AFIP (subidos o generados con el asistente Certificados ARCA).
4. Volvé a **importar el certificado** desde el asistente Certificados ARCA si cambiaste de ambiente (homologación ↔ producción).

## Referencias

- AFIP ARCA: [Administración de Certificados Digitales](https://serviciosweb.afip.gob.ar/clavefiscal/adminrel/verCertificado.aspx)
- Agregar certificado: [agregarCertificado.aspx](https://serviciosweb.afip.gob.ar/clavefiscal/adminrel/agregarCertificado.aspx)
