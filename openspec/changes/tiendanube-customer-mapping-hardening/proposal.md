# Propuesta: Endurecimiento mapeo manual de clientes Tienda Nube

## Intención

Reducir riesgos del flujo **New Customer** / `CustomerMapping` manual: duplicados en AdministraNET, vínculos incorrectos, sync silencioso y listado que oculta mapeos incompletos.

## Alcance

- Validación de existencia de IDs (Tienda Nube API + AdministraNET MySQL) en formulario.
- Anti-duplicado en `create_customer` (email/CUIT).
- Unicidad de `adminet_codigo` en mapeos Synap (migración).
- Listado con mapeos incompletos + filtro.
- Botón **Sincronizar ahora** visible (AJAX existente).
- Defaults seguros: `sync_enabled=False`, dirección unidireccional TN→Adminet al crear.

## Fuera de alcance

- Búsqueda/autocompletar IDs desde APIs en el formulario (fase posterior).
- Refactor completo de dos `create_customer` duplicados en `adminet_service`.
