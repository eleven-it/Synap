# Spec delta: ecom-pedido-masivo-sucursales

## ADDED Requirements

### REQ-MAS-01 — Matriz
El sistema MUST proveer pantalla desktop de carga masiva: filas = artículos; columnas = sucursales (`cliente_domicilio` no anulados del cliente). Cantidades MUST ser packs (misma semántica UOM que compra mayorista).

#### Scenario: Columnas por domicilio
- **GIVEN** cliente con 3 domicilios activos
- **WHEN** el vendedor abre pedido masivo para ese cliente
- **THEN** MUST ver 3 columnas de sucursal editables

### REQ-MAS-02 — Catálogo filtrado
Los artículos del buscador MUST restringirse a marcas asignadas en ternas del par (viajante, cliente).

### REQ-MAS-03 — Un PED por sucursal
Al confirmar, cada sucursal con suma de packs > 0 MUST generar un PED AdministraNET con `cliente_datos_adicionales.id_cliente_domicilio` correspondiente y `CodViajante` del vendedor.

### REQ-MAS-04 — Borrador persistente
El sistema MUST autoguardar la matriz en borrador Postgres. Tras cierre accidental o F5, el usuario MUST poder recuperar la carga desde el hub.

#### Scenario: Recuperación
- **GIVEN** borrador con celdas cargadas
- **WHEN** el usuario cierra el navegador y vuelve al hub
- **THEN** MUST poder Continuar y ver las mismas cantidades

### REQ-MAS-05 — Rollback sin pérdida
Si falla la creación de cualquier PED del lote, el sistema MUST NO dejar el lote a medias (compensar/anular creados en la corrida), MUST devolver el draft a BORRADOR con los datos de celdas intactos, y MUST mostrar errores por sucursal/artículo para corregir.

#### Scenario: Fallo a mitad de lote
- **GIVEN** 3 sucursales con cantidad y la 2.ª falla al grabar
- **WHEN** termina el intento de confirmación
- **THEN** MUST quedar 0 PED netos del lote, draft en BORRADOR, y mensaje de error de la sucursal 2

### REQ-MAS-06 — UI canon
La pantalla MUST seguir el patrón visual del Tablero de producción (header oscuro, matriz sticky, densidad desktop).
