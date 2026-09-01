# SYNAP-SYSTEM-MAP — Mapa Maestro del Sistema

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

```
USERS (Web / PWA / API clients)
   │
   ▼
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (SSR + Tailwind + Alpine.js + ES Modules)    │
│  theme/ · */templates/ · PWA (sw.js)                    │
└────────────────────────┬────────────────────────────────┘
                         │
   ┌─────────────────────┼─────────────────────┐
   ▼                     ▼                     ▼
/login/            /core/dashboard/      /reports/dashboard/
/ecom/pedidos/     /mpr/wizard/          /self_checkout/
/compras/captura/  /contabilidad/        /ia/
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  MIDDLEWARE STACK (12 middlewares)                       │
│  Session → MySQL pool → Auth → Modules → PWA Nivel A   │
└────────────────────────┬────────────────────────────────┘
                         │
   ┌─────────┬───────────┼───────────┬─────────┐
   ▼         ▼           ▼           ▼         ▼
 reports    ecom        mpr      self_chk    stock
 ventas    compras   contab     fe_afip    tiendanube
 captura   legacy_db   ia       odoo       logistica
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  CORE SERVICES                                         │
│  mysql_pool · permisos · module_manager · backup       │
│  administranet_types · legacy_mysql_schema             │
└────────┬───────────────────────────────┬──────────────┘
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────────┐
│  PostgreSQL 13  │            │  MySQL AdministraNET │
│  (Synap owned)  │            │  (per base_empresa)  │
│  ~100+ tables   │            │  ~200+ tables        │
└─────────────────┘            └──────────┬──────────┘
                                          │
         ┌────────────────────────────────┤
         ▼                ▼                ▼
   AdministraNET      administraNET     VB6 Clients
   VB6 (reference)    -ecom PHP
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
      AFIP/ARCA    Tienda Nube      Odoo 19
      (SOAP)       (REST)           (RPC)
         │
         ▼
      Redis 6 (cache)
         │
         ▼
   Support Platform (separate)
   Django+React+Celery+pgvector
```

---

## Relaciones laterales

| De | A | Tipo |
|----|---|------|
| ecom | administraNET-ecom PHP | HTTP relay |
| self_checkout | fe_afip | Import directo (CAE) |
| tiendanube | MySQL + TN API | Sync bidireccional |
| support | Synap API | HTTP JWT |
| reports | ventas | Import bidireccional |
| mpr | stock | Import bidireccional |
| legacy_db | contabilidad_audit | Import + shared tables |
| core | ALL modules | Hub (256 refs) |

---

## Preguntas de desconexión

| Si desconecto... | Se rompe... |
|------------------|-------------|
| MySQL AdministraNET | **Todo** — auth, datos, permisos |
| PostgreSQL | Metadatos, reportes config, IA, captura, módulos |
| Redis | Cache módulos (degraded), sin crash |
| core/ | **Todo** — pool, auth, permisos, módulos |
| fe_afip | TPV facturación, ecom NC |
| administraNET-ecom PHP | ecom relays (parcial — hay SQL directo) |
| Redis | Performance degradada, no funcional |
| support/ | Soporte RAG (independiente) |

---

*Generado por auditoría READ ONLY.*
