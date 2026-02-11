# pyafipws y Docker (padrón AFIP para FA/FB)

## Por qué aparece "Validación AFIP no disponible. Se usará Factura B."

El paquete **pyafipws** (instalado desde `requirements.txt` con `git+https://github.com/reingart/pyafipws.git`) incluye WSAA, WSFEv1 y otros módulos, pero en la estructura que se instala **no está el submódulo `ws_sr_padron_a5`**. Ese módulo se usa para consultar el padrón AFIP y decidir si emitir Factura A o B según el CUIT.

Por eso, en el kiosco (y en consultar-cuit) la app muestra el aviso en ámbar **"Validación AFIP no disponible. Se usará Factura B."** y permite seguir: se emite siempre Factura B cuando el padrón no está disponible.

## Comportamiento actual

- **Con pyafipws instalado:** CAE/CAEA (facturación electrónica) funciona; solo la **validación de condición fiscal por CUIT** (FA vs FB) no está disponible.
- **Sin el módulo padrón:** Se usa Factura B para todos los comprobantes que requieran validación por CUIT. No hace falta hacer nada más para que la app funcione.

## Si en el futuro hubiera un pyafipws con padrón A5

Si se publicara una versión o fork de pyafipws que instale correctamente `pyafipws.ws_sr_padron_a5`, bastaría con actualizar la dependencia en `requirements.txt` (o el Dockerfile) y reconstruir la imagen. La app ya está preparada para usar el padrón cuando el módulo exista.
