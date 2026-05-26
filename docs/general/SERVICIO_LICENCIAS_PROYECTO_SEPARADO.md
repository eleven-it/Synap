# Servicio de licencias y panel SaaS: proyecto separado de Synap

**Estado:** decisión de arquitectura.  
**Relación:** el repositorio **Synap** (Django, ERP) **no** aloja el servidor de tokens ni el panel global de activación de instancias.

---

## Decisión

| Componente | Dónde vive |
|------------|------------|
| API de licencia (heartbeat, emisión/renovación de tokens firmados, opcional lista de revocación) | **Proyecto aparte** (repositorio y despliegue propios) |
| Panel de control para operadores (alta/baja de clientes, suspender o revocar instalaciones, planes) | **Mismo proyecto aparte** (o front separado contra la misma API, según equipo) |
| Cliente en cada instalación Synap (settings, job periódico, cache de estado, middleware) | **Monorepo Synap** |

---

## Por qué separar

- Releases del ERP por cliente no deben acoplarse al panel comercial ni a rotación de claves de firma.
- Reduce superficie de ataque: secretos maestros y datos de contratos fuera del código de negocio.
- Permite evolucionar billing y UX del panel sin tocar `ventas/`, `core/`, etc.

---

## Contrato Synap → servicio de licencias

Synap solo necesita documentación estable de:

- URL base y versión de API soportada.
- Identificador de instalación y mecanismo de autenticación hacia el servicio.
- Formato del token o respuesta firmada (claims: estado, módulos permitidos, validez, gracia).

La **OpenAPI / especificación** del servicio debe mantenerse en el **repositorio del servidor de licencias**; en Synap se referencia la versión compatible en configuración y en diseño OpenSpec: `openspec/changes/presupuesto-ventas-synap/DESIGN_PUNTO13_ENTITLEMENT_Y_DESACTIVACION_REMOTA.md`.

---

## Referencias

- Diseño detallado (heartbeat, gracia offline, seguridad): `openspec/changes/presupuesto-ventas-synap/DESIGN_PUNTO13_ENTITLEMENT_Y_DESACTIVACION_REMOTA.md`
- Especificación funcional Presupuesto (trazabilidad): `SPEC_PRESUPUESTO_VENTAS_SYNAP.md` §12
