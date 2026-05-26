# Punto 13 — Entitlement, licenciamiento SaaS y desactivación remota (cerrado)

## Contexto

- **VB6** combinaba **licencia comercial** (`licencia_gestion`, …), **flags de módulo** (`mod_*` en `Principal`) y **permisos por puesto** (`permisos` / `permisos_sistema`). No existe un único “feature flag” tipo SaaS.
- **Synap** ya tiene **`ModuleConfig`** (activación técnica del módulo en PG) y permisos granulares alineados al menú legacy.
- Las **instalaciones pueden estar en servidores o nube del cliente**: no hay garantía de panel único ni de que Synap controle la infraestructura.

Este documento cierra **cómo pensar licenciamiento + desactivación remota** sin confundir capas.

---

## Modelo en capas (obligatorio conceptualmente)

Orden de evaluación recomendado para **acceso operativo** (lectura/escritura):

1. **Entitlement / licencia (organización / instalación)** — ¿el contrato o la suscripción permite este producto o módulo?
2. **Activación técnica** — ¿el código está desplegado y `ModuleConfig` (u equivalente) habilita la app?
3. **Permiso de menú / rol Synap** — ¿el puesto tiene el ítem?
4. **`permisos_sistema` (MySQL)** — reglas finas de negocio por puesto.

**Regla:** el entitlement **no** lo reemplazan los permisos legacy: un puesto no debe “activar gratis” un módulo no contratado.

---

## Licenciamiento tipo SaaS

- **Planes** definen conjuntos de **features / módulos** (y opcionalmente límites: usuarios, sucursales).
- Los datos de plan conviene mantenerlos en **PostgreSQL (Synap)** y/o un **servicio de billing** que actualice estado de suscripción.
- **`ModuleConfig.is_active`** sigue siendo el interruptor **técnico** de “esta instancia tiene el módulo cargado”; el **plan** define si **corresponde** al cliente.

Equivalencia transparente con legado: perfiles tipo Basic/Small/PV pueden **mapearse** a planes actuales en documentación comercial, sin copiar nombres en código obligatoriamente.

---

## Desactivación remota con instalación en infra del cliente

Objetivo: poder **suspender** el uso del sistema (o de módulos) cuando corresponda contractualmente, **sin** depender de que alguien entre al servidor del cliente, asumiendo que la instalación puede **salir a Internet** (directo o vía proxy corporativo).

### Principios

- **Transparencia contractual:** el contrato/licencia debe contemplar verificación periódica y consecuencias de impago o fin de servicio.
- **No “backdoor” opaco:** el mecanismo debe ser **verificable** (HTTPS, respuestas firmadas o tokens auditables), no ejecución remota arbitraria.
- **Resiliencia operativa:** cortes de red del cliente **no** deben bloquear en frío inmediato; se usa **período de gracia offline** configurable.

### Mecanismos a evaluar (combinables)

| Enfoque | Idea | Pros | Contras |
|--------|------|------|---------|
| **A — Heartbeat / well-known URL** | Proceso periódico (cron/worker) consulta un endpoint de licencia; respuesta indica `active`, `suspended`, fecha límite, módulos permitidos. | Centralizado; revocación rápida. | Requiere salida HTTPS; hay que definir timeouts y fallos. |
| **B — Token firmado de corta vida** | Servidor de licencias emite JWT o blob firmado (clave pública embebida o rotación); la instancia renueva antes de vencer; offline hasta `grace_period`. | Menos llamadas; funciona en air-gap limitado con gracia. | Gestión de claves y renovación; reloj del servidor debe ser fiable. |
| **C — Lista de revocación** | Además de A/B, comprobar si `installation_id` está en lista de denegación publicada (CDN/signed JSON). | Revocación de emergencia sin depender solo del último heartbeat. | Complejidad operativa; cache y TTL. |
| **D — Solo operación local** | Variable `ENV` o fichero en disco activado por soporte remoto al cliente (VPN, acceso acordado). | Sin dependencia de salida a Internet. | **No** es desactivación remota directa; es manual. |

### Recomendación de diseño (para implementación futura)

- **Primario:** **A + B** — heartbeat periódico que obtiene **estado + token firmado** con validez y **ventana de gracia** si no hay respuesta (ej. último estado conocido “válido” hasta N días).
- **Complementario:** **C** si el negocio exige revocación en horas sin esperar al siguiente heartbeat.
- **Fallback operativo:** **D** documentado para clientes sin salida a Internet (solo soporte + política contractual distinta).

### Configuración típica (nombres orientativos)

- URL base del servicio de licencia (configurable; proxy corporativo).
- Identificador de **instalación** / tenant y credencial no secreta o certificado de cliente si aplica.
- **`grace_offline_days`**, timeouts, comportamiento en fallo de red: **último estado válido** vs **modo solo lectura** vs **bloqueo total** (definir por producto/legal).

### Seguridad

- TLS obligatorio; opcional **certificate pinning** solo si se documenta rotación.
- Respuestas **firmadas** (clave del proveedor) para evitar spoofing por DNS malicioso en la red del cliente.
- Registrar **auditoría local** de cambios de estado (suspended, revoked) sin exponer datos sensibles del cliente al log.

---

## Proyecto separado: servidor de tokens + panel de control SaaS

**Decisión:** el **servidor de emisión/validación de tokens**, la **API de heartbeat**, el **almacenamiento maestro de instalaciones/clientes** y el **panel administrativo** para activar, suspender o revocar instancias **no** forman parte del monorepo **Synap**. Se implementan como **proyecto(s) aparte** (repositorio y despliegue propios).

### Motivos

- **Ciclo de vida distinto:** despliegues del panel y del servicio de licencias no deben acoplarse a releases de aplicación Django por cliente.
- **Superficie de seguridad:** claves de firma, base de contratos y auditoría de operadores conviene aislarlas del código de negocio ERP.
- **Equipos:** producto/SaaS ops puede evolucionar billing y UX del panel sin tocar `ventas/`, `reports/`, etc.

### Qué permanece en Synap (este repo)

- **Cliente ligero:** settings (`SYNAP_LICENSE_URL` o equivalente), `installation_id`, renovación periódica (cron/Celery/worker), cache del último estado firmado y política de gracia offline.
- **Middleware o helper** que combine entitlement con `ModuleConfig` y permisos.
- **Sin** UI de administración global de tenants en Synap salvo que el producto decida un panel mínimo interno (no recomendado si ya existe proyecto dedicado).

### Contrato entre proyectos (a especificar en el repo del servicio)

- Endpoints documentados: renovación de token, estado de instalación, opcional CRL/revocación.
- Formato de claims en JWT o payload firmado (instalación, plan, módulos, `valid_until`, `grace_until`).
- Autenticación del cliente (clave de instalación, mTLS o similar).
- Versionado de API para no romper instancias antiguas.

La especificación OpenAPI o documento equivalente debe vivir en el **proyecto del servidor de licencias**; Synap solo referencia versiones soportadas en `settings`/documentación.

---

## Alcance respecto al cambio PRE

- Este punto **cierra el diseño conceptual** para Presupuesto y el resto de ventanas que dependan del mismo **patrón de plataforma**.
- La **implementación** del cliente de licencia en Synap (middleware, settings) es **transversal**; las vistas PRE deben **respetar** el estado global cuando exista el servicio.
- La **implementación del servidor y del panel** corresponde al **proyecto separado** descrito arriba.

---

## Referencias internas

- Resumen “proyecto aparte”: `docs/general/SERVICIO_LICENCIAS_PROYECTO_SEPARADO.md`
- Menú y licencias VB6: `docs/general/PRINCIPAL_FRM_INFORME_DETALLADO.md` (§ módulos y licencias, `Inicia_Menu_Rapido`).
- Módulos Synap: `core/module_manager.py`, `core/models/module_config.py`, `docs/general/INFORME_ESTADO_APPS_MODULOS.md`.
