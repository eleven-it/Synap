# Una empresa por base de datos en AdministraNET

## Conclusión

En AdministraNET (VB6) **solo existe una empresa por base de datos MySQL**. Por tanto, en Synap la pantalla "Datos empresa" debe mostrar directamente los datos de esa empresa única (vista de detalle/edición), no una lista de tarjetas.

---

## ¿Datos de empresa en base_empresa o en otra DB?

**Los datos de empresa (DatosEmpresa) se encuentran y se guardan en la base de la empresa seleccionada (base_empresa). No se recuperan desde otra base.**

- En el login (IngresoUsuario) el usuario elige una empresa; la **cadena de conexión** (IngresoUsuario.Conex) se configura para apuntar a la base de esa empresa (base_empresa).
- Esa misma conexión es la que usa **Principal** y todos los formularios posteriores, incluido **Empresa.frm** (Datos de la empresa).
- Por tanto, al abrir Empresa.frm, el RecordSource `SELECT * FROM DatosEmpresa` se ejecuta contra la base ya conectada, es decir **base_empresa**. No hay lectura de DatosEmpresa desde una base central ni desde otra DB.

La única base “distinta” es **`empresas`**: se usa **solo en el login** para obtener la lista de empresas (id_empresa, nombre_empresa, base_empresa) y elegir a cuál conectarse. Los datos maestros de la empresa (nombre, CUIT, domicilio, etc.) viven en la base indicada por base_empresa (ej. administranet89).

Referencia: [MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](MIGRACION_ADMINISTRANET_VB6_ANALISIS.md) § 3.1 (Dependencias VB6: IngresoUsuario.Conex); [PRINCIPAL_FRM_INFORME_DETALLADO.md](PRINCIPAL_FRM_INFORME_DETALLADO.md) (uso de IngresoUsuario.Conex).

---

## Evidencia en la estructura

### 1. Modelo multi-empresa: una base por empresa

- La multi-empresa se resuelve con **una base MySQL por empresa** (no varias empresas en una misma base).
- En el login, el usuario elige una **empresa** desde la tabla `empresas` (base `empresas`), que devuelve `base_empresa` = nombre de la base de datos (ej. `administranet89`) y `nombre_empresa` = etiqueta visible (ej. `Prueba`).
- La sesión guarda `base_empresa` (uso interno) y `nombre_empresa` (pie de estado, margen derecho) para identificar con qué DB se trabaja **sin** mostrar el nombre técnico de la base.
- La sesión queda asociada a esa única `base_empresa`; todo el trabajo se hace contra esa base.

Referencia: [SYNAP_ALINEACION_ADMINISTRANET_Y_GAPS.md](SYNAP_ALINEACION_ADMINISTRANET_Y_GAPS.md) — "Multi-empresa por base: una base MySQL por empresa".

### 2. Tabla DatosEmpresa: un solo registro en la práctica

- En cada base (ej. `administranet89`) la tabla **DatosEmpresa** contiene **un solo registro relevante**.
- En VB6 (Empresa.frm): *"DataEmpresa (MSADODC): enlazado a DatosEmpresa. **Un solo registro (id_empresa = 1 en la práctica)**."*
- En el resto del código VB6 se usa siempre `id_empresa = 1` para leer datos de la empresa (Facturacion.frm, Pedido_Avanzado.frm, Lista_Comp_Fact.frm, CargaComprobantesPed.frm, etc.):  
  `SELECT * FROM datosempresa WHERE id_empresa = 1`.

Referencia: [MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](MIGRACION_ADMINISTRANET_VB6_ANALISIS.md) § 3.1; [general/tablas/datosempresa.md](tablas/datosempresa.md).

### 3. Implicación para Synap

- No tiene sentido una **lista** de empresas (grid de tarjetas) cuando por construcción solo hay **una** empresa por base.
- Lo correcto es: al entrar en "Datos empresa" (o equivalente), **ir directo a la vista de detalle/edición** de esa empresa única.
- Si en la base no hay registro en DatosEmpresa (tabla vacía o inexistente), entonces sí mostrar estado vacío y opción "Crear primera empresa".

---

## Comportamiento implementado en Synap

- **Ruta "Datos empresa"** (`core:empresa_listar`):
  - Si existe empresa en la base activa → **redirección a la pantalla de detalle/edición** (empresa única).
  - Si no existe → se muestra el estado vacío con aviso y botón "Crear primera empresa".
- La vista de detalle/edición es la misma que en AdministraNET (Empresa.frm): un formulario con los datos de la única empresa de la base.
