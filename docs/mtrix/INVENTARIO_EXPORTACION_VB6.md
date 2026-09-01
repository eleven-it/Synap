# Inventario de exportación Accera V.3.5 → Mtrix

No hay formularios VB6: el origen es un exe desatendido (`Unattended=-1`, `Startup=Sub Main`). Este inventario cubre generadores, config y artefactos. La paridad de CSV se mide contra este documento y contra `Principal.bas`.

**Origen:** `/Users/sebastian/Documents/Accera/ACCERA V.3.5/Software/Principal.bas` (1808 líneas).  
**Fuera de alcance:** `ACCERA V anterior` (layout `H;` / `V;` / `E`).

## 1. Configuración (`config.ini`)

| Clave | Sección | Uso en V.3.5 | Equivalente Synap |
|-------|---------|--------------|-------------------|
| `servidor`, `Puerto` | DatosPrincipales | Conexión MySQL | Pool Synap (`base_empresa`); no se replica |
| Usuario/clave/base | Hardcode en `.bas` | Credenciales | **No migrar.** Pool + sesión |
| `FechaPersonalizada` | DatosPrincipales | Si/No | `MtrixConfig` |
| `FechaInicio`, `FechaFinal` | DatosPrincipales | Rango si personalizada | `MtrixConfig` |
| `DiasAProcesar` | DatosPrincipales | Default 5 si no personalizada | `MtrixConfig` |
| `CodigoProveedorPrincipal` | MTRIX | Vacío=todos; lista CSV | `MtrixConfig` |
| `CNPJFornecedor` | MTRIX | Sin prefijo `AR` (en Accera era un ID de portal) | En Synap: CUIT de `datosempresa` (no se carga a mano). Prefijo `AR` al serializar |
| `pvnf` | MTRIX | No=solo `punto_venta.cont='Si'` (solo VD) | `MtrixConfig` |
| `log` | MTRIX | Si/No | Log de job Synap (siempre auditable) |
| `MultiplicadorCantidad` | MTRIX | Default 1 | `MtrixConfig` |
| `MultiplicadorPrecio` | MTRIX | Default 1 | `MtrixConfig` |
| `VersionLayout` | MTRIX | 19; **no** va en el nombre de archivo | Conservar en config; no usar en filename |

## 2. Generadores (contrato de exportación congelado)

Orden de `Sub Main`: CI → PD → ES → VD → FV.

| Código | Función VB6 | Tablas MySQL | Filtro proveedor | Fechas | `pvnf` |
|--------|-------------|--------------|------------------|--------|--------|
| CI | `GenerarCI_MTRIX` | `cliente`, `distrito`, `departamento`, `provincia`, `tipo_cliente`, `cuentacliente` | No | Sí (clientes con ventas en el período) | Calculado, no aplicado |
| PD | `GenerarPD_MTRIX` + `_Proveedor` | `articulo`, `marca`, `rubro`, `datosempresa` | Sí (1/N/todos) | No (`DT_ARQUIVO` = fecha fin) | No |
| ES | `GenerarES_MTRIX` + `_Proveedor` | `stock_deposito`, `articulo` | Sí | No (`DT_ESTOQUE` = fecha fin) | No |
| VD | `GenerarVD_MTRIX` + `_Proveedor` | `cuentacliente`, `stock`, `articulo`, `cliente`, `departamento`, `punto_venta` | Sí | Sí | **Sí** |
| FV | `GenerarFV_MTRIX` | `cuentacliente`, `cliente`, `viajantes` | No | Sí (Synap: un registro por CUIT; VB6: por CUIT + `cliente.Codigo`) | No |

Nombre de archivo: `{TIPO}-INT{ddmmyyyyhhmmssSSS}.csv` (sin versión). Delimitador `;`. Header en la primera línea. Encoding de producción VB6: latin1 en la conexión; Synap debe emitir el mismo contenido de campos.

### Headers CSV (exactos)

```
CI: CNPJ_FORNECEDOR;CNPJ_DISTRIBUIDOR;CNPJ_CLIENTE;RAZAO_SOCIAL;ENDERECO;BAIRRO;CEP;CIDADE;ESTADO;NOME_RESPONSAVEL;TELEFONE;CNPJ_CLIENTE;ROTA;TIPO_LOJ;REPRESENTATIVIDADE
PD: DT_ARQUIVO;CNPJ_DISTRIBUIDOR;CNPJ_FORNECEDOR;RAZAO_SOCIAL_FORNECEDOR;CODIGO_PRODUTO;TIPO_EMBALAGEM;EAN;TIPO_COD_BARRAS;DESCRICAO;DIVISAO;STATUS
ES: DT_ESTOQUE;CNPJ_FORNECEDOR;CNPJ_DISTRIBUIDOR;EAN;QTDE_TOTAL
VD: CNPJ FORNECEDOR;CNPJ DISTRIBUIDOR;COD CLIENTE;DATA;NOTA_FISCAL;EAN;QTDE;PRECO;VENDEDOR;TIPO DE DOCUMENTO;CEP
FV: CNPJ FORNECEDOR;CNPJ AGENTE DISTRIBUICAO;IDENTIFICACAO CLIENTE;CODIGO DO GERENTE;NOME DO GERENTE;CODIGO DO SUPERVISOR;NOME DO SUPERVISOR;CODIGO DO VENDEDOR;NOME DO VENDEDOR
```

### Reglas que no se tocan

- Prefijo `AR` + `CNPJFornecedor` en fornecedor.
- Distribuidor = `datosempresa.CUIT` sin guiones.
- Consumidor final / CUIT `0` → `99999999999` en **CI y VD**. FV escribe el CUIT crudo (`0` si no hay CUIT); no aplica `ObtenerCNPJClienteMTRIX`.
- CI: `CNPJ_CLIENTE` duplicado (cols 3 y 12). `NOME_RESPONSAVEL=NA`, `ROTA=RUTA`.
- CI: solo clientes con ventas en el período; `REPRESENTATIVIDADE` como en el SQL VB6 (`FORMAT` `de_DE`, 2 decimales).
- CEP (CI y VD): si no hay código postal, viene `0`, solo ceros, `NA` o tiene menos de 4 dígitos, Synap informa **`9400`** (CEP más frecuente en la base: SMART CLEAN / Río Gallegos). Diversey no acepta CEP `0`; VB6 ponía `0`.
- PD: código = `codartprov` (`SanitizarCampoCSV` vacío → `NA`); `DIVISAO` = marca si no es Null/vacío (incluye `-Ninguno-`) → rubro → `OTROS PRODUCTOS`; `STATUS` I/A según `discontinuo`; razón social fornecedor = `datosempresa.Nombre`.
- ES: `SUM(saldo)` donde `saldo >= 0`.
- EAN: no se emite `0` ni vacío. Si no hay `NroCodBarraF`, se usa `codartprov` o `IDArt`. Artículos sin EAN válido y **sin ventas** en el período se omiten de PD y ES (requisito Diversey).
- VD: excluye `Anulado='Si'` y `REC`. FA/FB cantidad positiva tipo `N`. NC/ND cantidad negativa tipo `N`. Agrupa por factura+EAN+fecha+**COD_CLIENTE crudo**+vendedor+tipo+CEP (no por el `99999999999` de pantalla) y suma cantidad y precio (`PrecioVentaxU`). El CSV emite el CNPJ ya normalizado.
- FV: gerente `1`/`GERENTE GENERAL`, supervisor `1`/`SUPERVISOR`. Sin tablas nuevas de jerarquía. **Synap colapsa a un registro por CUIT** (`IDENTIFICACAO CLIENTE`); si hay varios vendedores elige el de menor `COD_VENDEDOR` (empate por nombre). VB6 agrupaba también por `cliente.Codigo`.
- Sin archivo si el recordset está vacío.
- **Un CSV por categoría por corrida** (máximo CI, PD, ES, VD, FV). VB6 recorre `CodigoProveedorPrincipal` y escribe un archivo por código; Synap **no replica ese loop**: si hay lista (`23,29,31`) filtra `CodigoProveedor IN (...)` en **una** consulta y emite un solo archivo. Vacío = todos los proveedores, un archivo.

## 3. Operativa de archivos (VB6 → Synap)

| VB6 | Synap |
|-----|-------|
| `Procesados\` | Artefactos del job (storage) |
| `Historico\yyyyMMdd_HHmmss\` | Jobs anteriores (no borrar al generar) |
| `Salida\` / `Salida.Respaldo\` | Descarga ZIP/CSV + envío SFTP |
| `PrevInstance` | Un job activo por `base_empresa` |
| Tray balloon / log txt | Progreso de job + log persistido |

## 4. Componentes UI Synap (nuevos; no existen en VB6)

El VB6 no tiene pantalla. Equivalencias de validación:

| Necesidad | Pantalla Synap | Canon |
|-----------|----------------|-------|
| Ver datos antes de exportar | Preview por tipo (CI/PD/ES/VD/FV) | Tabla densa MPR/`opt_list` + filtros reportes |
| Ajustar parámetros | Configuración | Formulario MPR, toggles Activo/Inactivo, buscador predictivo de proveedores (kardex/MPR) |
| Disparar ahora | Hub + CTA Generar | Hero MPR + modal confirmación |
| Enviar al portal | Config SFTP + acción Enviar | Modal operativa; reutilizar patrón paramiko de backup |
| Programar | Programador en config | Calendario/hora como `/core/backups/configuracion/` |
| Historial | Listado de jobs | `opt_list` / jobs Odoo |

Preview **formatea** para humanos (fechas `dd/MM/yyyy`, números en español). El CSV de exportación **no** usa ese formato: sale igual que V.3.5.
