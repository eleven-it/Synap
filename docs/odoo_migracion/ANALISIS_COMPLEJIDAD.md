# Análisis de complejidad — Migración Odoo

Resumen ejecutivo del plan de migración AdministraNET → Odoo 19. Detalle completo en el plan SDD del repositorio.

## Escala de complejidad

| Dominio | Complejidad | Fase |
|---------|-------------|------|
| Rubros / subrubros / marcas | Baja | F3 |
| Datos empresa | Media | F3 |
| Vendedores (`viajantes`) | Media | F3 |
| Clientes / proveedores | Alta | F3 |
| Artículos | Alta | F4 |
| Saldos stock | Crítica | F4 |
| Facturas CC abiertas | Crítica | F5 |

## Prerrequisitos P0

Artículos, depósitos, UoM, contribuyentes/IVA, sucursales/PV/talonarios, plan de cuentas (si contabilidad Odoo).

## Implementación Synap

| Fase | Estado | Artefactos |
|------|--------|------------|
| F0 Discovery | Implementado | `odoo_discovery`, UI inventario |
| F1 Fundación | Implementado | App, JSON-2, conexiones |
| F2 Mapeos doc | Implementado | `docs/odoo_migracion/MAPEO_CAMPOS_*.md` |
| F3 Maestros | Implementado | extractors + loaders partners/catálogos |
| F4 Productos/stock | Implementado | artículo + stock pendiente wizard |
| F5 Facturas | Implementado | mapping pendiente manual (sin CAE) |
| F6 Convivencia | Implementado | wizard, validación, reglas |

## Riesgos

- Doble emisión fiscal → solo histórico en Odoo
- Desbalance stock → cuadre en validación + wizard ajuste Odoo
- Sin FKs MySQL → validación de integridad en discovery
