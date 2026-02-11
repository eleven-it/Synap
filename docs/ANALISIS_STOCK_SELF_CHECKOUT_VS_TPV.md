# Análisis: diferencias entre registros `stock` (Self-Checkout vs TPV)

## Registros comparados

| Origen           | id_stock | CodigoMovimiento | IDArt | Comentario                          |
|------------------|----------|------------------|-------|-------------------------------------|
| **Self-Checkout**| 138998   | 62771            | 1481  | Creado por kiosco (31/01/2026)     |
| **TPV administraNET** | 138517 | 44631        | 4161  | Creado por TPV VB6 (12/11/2025)    |

---

## Campos con diferencia relevante

### 1. Cabecera / identificación del movimiento

| Campo             | Self-Checkout (138998) | TPV (138517)     |
|-------------------|------------------------|------------------|
| **Fecha**         | vacío                  | 12/11/2025       |
| **CodigoArticulo**| vacío                  | 22.3.15          |
| **Descripcion**   | vacío                  | Coony Collagen Eye Zone Mask |
| **Tipo**          | vacío                  | Cliente          |
| **Comprobante**   | FB                     | FB               |
| **TipoComp**      | vacío (antiguos) / Venta Self Checkout (nuevos) | Venta TPV        |
| **NroComprobante**| vacío (o 1)            | 0006-00000031    |
| **CodigoCP**      | vacío                  | 1 (id cliente)   |
| **CodDeposito**   | vacío                  | 3                |
| **CodSucursal**   | vacío                  | 4                |
| **IdUsuario**     | 0                      | 34               |
| **CodViajante**   | vacío                  | 1                |
| **CodLaboratorio**| vacío                  | 0                |

### 2. Saldo y cantidades

| Campo    | Self-Checkout | TPV  |
|----------|---------------|------|
| **saldo**| 0,00          | 1    |
| Entrada  | 0,00          | 0,00 |
| Salida   | 1             | 1   |

En TPV, **saldo** = saldo en depósito después de la salida. En el registro del kiosco queda 0 porque no se estaba persistiendo.

### 3. Precios e IVA (todos vacíos/0 en Self-Checkout)

| Campo            | Self-Checkout | TPV (ejemplo) |
|------------------|---------------|----------------|
| PrecioCostoxU    | vacío         | 5979           |
| PrecioVentaxU    | vacío         | 10742,9752     |
| PrecioBrutoxU    | vacío         | 12999          |
| PrecioIVAxU      | vacío         | 2256,02…       |
| PrecioNetoxU     | vacío         | 10742,97…      |
| PrecioCostoxR    | vacío         | 5979           |
| PrecioVentaxR    | vacío         | 10742,9752     |
| PrecioBrutoxR    | vacío         | 12999          |
| PrecioNetoxR     | vacío         | 10742,9752     |
| PrecioIVAxR      | vacío         | 2256,0248      |
| **Alicuota**      | vacío         | 21             |
| **AlicuotaIB**   | vacío         | 3,5            |
| **imp_alicuota_iva**  | 0,00     | 21             |
| **imp_alicuota_iibb** | 0,00     | 3,5            |
| **TipoIVA**      | vacío         | Gravado        |

### 4. Otros

| Campo       | Self-Checkout | TPV      |
|-------------|---------------|----------|
| Orden       | 1             | 214521 (o 36) |
| detalle     | vacío         | texto renglón |
| id_manual   | vacío         | 40000027 |
| FechaControl| 31/01/2026…   | 12/11/2025… |

---

## Conclusión

El registro **138998** (Self-Checkout) se generó **antes** de la alineación en `confirmation_service.py`: faltan Fecha, CodigoArticulo, Descripcion, Tipo, TipoComp, NroComprobante, CodigoCP, CodSucursal, CodDeposito, IdUsuario, CodViajante, Saldo y todos los precios/alícuotas.  
El registro **138517** (TPV) tiene todos esos campos completos.

A partir de la alineación ya implementada, los **nuevos** movimientos de stock creados por el Self-Checkout se persisten con los mismos campos que el TPV (Fecha, CodigoArticulo, Descripcion, Tipo, TipoComp, NroComprobante, precios, alícuotas, Saldo, CodViajante, etc.).

Para los **registros antiguos** de stock (por ejemplo el 62771 / id_stock 138998) se puede:

1. Dejarlos como están (solo impacto en reportes/consultas que usen esos campos).
2. Ejecutar un **UPDATE** que complete Fecha, CodigoArticulo, Descripcion, Tipo, TipoComp, NroComprobante, CodigoCP, codSucursal, CodDeposito, Saldo, precios y alícuotas desde `articulo` y desde `cuentacliente`/talonarios por `CodigoMovimiento`.

Si quieres, el siguiente paso puede ser un script SQL de actualización solo para los movimientos de stock del Self-Checkout (por ejemplo los que comparten CodigoMovimiento con los 3 comprobantes 10764, 10765, 10766).
