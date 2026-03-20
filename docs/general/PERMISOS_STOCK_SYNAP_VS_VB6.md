# Permisos Stock: equivalencia Synap vs VB6 (CargaMovStock)

Resumen de cómo se recrean en Synap los mismos accesos que el formulario **CargaMovStock** (Ingreso Mov. Stock) en AdministraNET VB6.

## Fuentes de permiso en VB6

| Fuente | Tabla | Uso |
|--------|--------|-----|
| Visibilidad ítem menú | **permisos** | Clavemenu = `keyCompStock`, IDpuesto, Permiso = '1'. Principal.frm muestra u oculta "Ingreso Mov. Stock". |
| Comportamiento en el formulario | **permisos_sistema** | Una fila por IDPuesto: cambia_deposito, acceso_ref_movstock, acceso_motivo_movstock, id_refmovstock, id_deposito, etc. |

## Cómo Synap considera el acceso

| Aspecto | En Synap |
|--------|----------|
| **Ver ítem "Ingreso Mov. Stock" y acceder a la vista** | El usuario debe tener `stock.crear_movimiento`. Este permiso se obtiene de **permiso_sistema_puesto** o, si no está ahí, de la tabla **permisos**: si el puesto tiene Clavemenu `keyCompStock` con Permiso = '1' (o 'Si'), se otorga automáticamente `stock.crear_movimiento`. |
| **Comportamiento (depósitos, referencia, motivos)** | Se lee de **permisos_sistema** (misma tabla que VB6). Se edita en Synap en "Permisos del sistema" por puesto. |

## Mapeo Clavemenu → key_permiso

Definido en `core.constantes_permisos.MAPEO_MENU_A_PERMISO`:

| Clavemenu (permisos) | key_permiso (permiso_sistema / Synap) |
|----------------------|----------------------------------------|
| keyCompStock | stock.crear_movimiento |
| keyConsultaStock | stock.consultas |
| keyConsultaStockRap | stock.consultas |
| keyInformesStock | stock.informes |

## Dónde se asignan en Synap

- **Roles / permisos del menú:** al asignar o quitar ítems del menú para un puesto (p. ej. "Ingreso Mov. Stock"), se escribe en la tabla **permisos** y, para las Clavemenu mapeadas, se sincroniza **permiso_sistema_puesto** (valor 'Si') para que el puesto tenga el mismo acceso en Synap.
- **Permisos del sistema:** en la pantalla "Permisos del sistema" por puesto se editan los flags de comportamiento (cambia_deposito, acceso_ref_movstock, acceso_motivo_movstock, etc.) en la tabla **permisos_sistema**.

## Referencias

- [ESQUEMA_TABLAS_STOCK_MIGRACION.md](ESQUEMA_TABLAS_STOCK_MIGRACION.md) sección 2 y 2.1.
- [MODULO_STOCK_SYNAP.md](MODULO_STOCK_SYNAP.md): URLs, API y flujo de alta.
- `core.services.administranet_permisos_usuario.get_permisos_totales_administranet`: lectura desde permiso_sistema_puesto + permisos.
- `core.services.administranet_permisos_menu.AdministraNETPermisosMenuService.guardar_permisos_puesto`: escritura en permisos + sincronización a permiso_sistema_puesto.
