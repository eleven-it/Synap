# Investigación Profunda de Arquitectura — Synap

**Fecha:** 1 de marzo de 2026
**Autor:** Arquitecto de Software (sesión automatizada)
**Rama:** Desarrollo
**Alcance:** Proyecto completo (código, infraestructura, documentación, estado operativo)

---

## 1. Resumen Ejecutivo (20 bullets)

1. **Synap** es una plataforma web Django 4.2 que reemplaza progresivamente la app de escritorio **AdministraNET (VB6)** para gestión comercial y ERP.
2. La **base de datos dual** (PostgreSQL para Django/Synap + MySQL para AdministraNET) es la decisión arquitectónica más relevante y fuente de mayor complejidad.
3. Hay **8 apps Django propias instaladas**: core, login, dashboard, reports, self_checkout, stock, compras, mpr. Otras 14+ apps están comentadas en settings.
4. La autenticación se hace **directamente contra MySQL** (tabla `usuarios` de AdministraNET con AES), no contra el sistema auth de Django; se usa un `AdministraNETUser` mock como usuario en request.
5. El **pool MySQL** (`core/mysql_pool.py`) es el patrón único para todo acceso a AdministraNET; thread-safe, context managers, usado por login/reports/self_checkout/stock/compras/mpr.
6. **Reportes** es el módulo más maduro: definiciones en PostgreSQL (`ReportDefinition`), ejecución de queries contra MySQL, exportación Excel/PDF, catálogo por empresa/slug.
7. **Self-Checkout / TPV** tiene un flujo de confirmación atómico (codmov, talonarios, cuentacliente, stock, series, FE) alineado con VB6, pero **caja solo funciona si MercadoPago está instalado** (actualmente comentado).
8. **Stock** es operativo: alta de movimientos, consultas, ficha, PDF comprobante, ABM referencias; escritura transaccional en MySQL con rollback.
9. **MPR (Manufactura/Producción)** es un módulo nuevo con modelos en PostgreSQL (Opt, OptLinea, OptMaterial) que orquesta OPT/OPP/Armado contra tablas MySQL de producción.
10. **Compras** implementa Remito de Compra con paridad VB6 (PRemito.frm), temporales por usuario, importación de comprobantes.
11. La migración del **menú Archivo VB6** está parcialmente hecha: Datos empresa y Sucursales operativas; Entidades (Cliente, Proveedor, etc.) siguen en VB6.
12. **fe_afip** existe como código huérfano en el repo (no instalada, no en URLs, no en registry).
13. **Support** es un subproyecto independiente (React + Django) para RAG/copiloto con LangChain; se comunica con Synap solo vía API HTTP.
14. La UI usa **Tailwind CSS** (via django-tailwind) con tema propio (`theme/`); Crispy Forms con pack Tailwind; Material Icons.
15. Infraestructura Docker: contenedor app (python:3.10-slim), PostgreSQL 13, Redis 6-alpine; MySQL **externo** (no en docker-compose principal); Cloudflare CDN en producción.
16. Hay **archivos duplicados** significativos en self_checkout (`* 2.py`) y docs (`* 2.md`, `* 3.md`) que deben limpiarse.
17. El sistema de **permisos** lee de MySQL (`permiso_sistema_puesto`) y se expone vía middleware y context processors; el usuario `supervisor` tiene permisos hardcodeados.
18. La **documentación** es extensa (>60 docs en /docs/) pero tiene secciones obsoletas, duplicadas y con referencias a módulos no instalados.
19. No hay **CI/CD** visible ni pipeline de tests automatizado; el flujo es Desarrollo → Staging → Producción por merge manual.
20. El **entrypoint Docker** ejecuta migraciones, fix de migraciones y setup de reports automáticamente al iniciar el contenedor.

---

## 2. Mapa de Arquitectura Actual

### 2.1 Componentes principales

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAVEGADOR / UI                           │
│  Tailwind CSS · Material Icons · Crispy Forms · JS vanilla      │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS (Cloudflare en producción)
┌──────────────────────────────▼──────────────────────────────────┐
│                   DJANGO 4.2 (Gunicorn / runserver)             │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐  │
│  │  login    │ │  core    │ │ dashboard │ │     theme        │  │
│  │ (auth    │ │ (empresa,│ │ (redirect │ │ (templates,      │  │
│  │  MySQL)  │ │  sucur., │ │  a core)  │ │  static, TW CSS) │  │
│  └──────────┘ │  users,  │ └───────────┘ └──────────────────┘  │
│               │  permisos│                                      │
│  ┌──────────┐ │  stock   │ ┌───────────┐ ┌──────────────────┐  │
│  │ reports  │ │  svc)    │ │self_check-│ │     compras      │  │
│  │ (catálog │ └──────────┘ │  out/TPV  │ │ (remito compra)  │  │
│  │  queries │              │ (kiosk,   │ └──────────────────┘  │
│  │  export) │ ┌──────────┐ │  cart, FE,│ ┌──────────────────┐  │
│  └──────────┘ │  stock   │ │  confirm) │ │       mpr        │  │
│               │ (movim., │ └───────────┘ │ (OPT, OPP,       │  │
│  ┌──────────┐ │  ficha,  │               │  Armado, Lista    │  │
│  │ fe_afip  │ │  refs)   │ ┌───────────┐ │  materiales)     │  │
│  │ (huérfan)│ └──────────┘ │  support  │ └──────────────────┘  │
│  └──────────┘              │ (indep.)  │                        │
│                            └───────────┘                        │
│  Middleware: RequestUser · AdminAccess · DeviceDetection ·      │
│    ModuleMiddleware · ModulePermission · ModuleContext ·         │
│    ModuleCache · AjaxLoginRequired                              │
└──────────┬──────────────────────────────────┬───────────────────┘
           │                                  │
    ┌──────▼──────┐                   ┌───────▼──────────┐
    │ PostgreSQL  │                   │  MySQL externo   │
    │   (Synap)   │                   │ (AdministraNET)  │
    │             │                   │                  │
    │ - Empresa   │                   │ - usuarios       │
    │ - Branch    │                   │ - sesion         │
    │ - Usuarios  │                   │ - datosempresa   │
    │   Extendido │                   │ - sucursales     │
    │ - ModuleCfg │                   │ - articulo       │
    │ - ReportDef │                   │ - stock/stockp   │
    │ - Opt/Linea │                   │ - cuentacliente  │
    │ - Country   │                   │ - caja/caja_saldo│
    │ - State     │                   │ - codmov         │
    │ - FiscalResp│                   │ - talonarios     │
    │ - Currency  │                   │ - punto_venta    │
    │ - UOM       │                   │ - proveedor      │
    │ - django_*  │                   │ - cliente        │
    └─────────────┘                   │ - permiso_sistema│
                                      │ - lista_prod_*   │
    ┌─────────────┐                   │ - movimiento_stk │
    │   Redis     │                   │ - 200+ tablas    │
    │  (cache,    │                   └──────────────────┘
    │   sesiones) │
    └─────────────┘
```

### 2.2 Flujo de datos principal

```
Login → MySQL (empresas, usuarios, sesion) → session Django
     → context_processors → empresa_activa, permisos, menú
     → Reportes: ReportDefinition (PG) → query_runner (MySQL) → HTML/Excel/PDF
     → Self-Checkout: cart/kiosk → confirmation_service (MySQL transaccional)
     → Stock: alta_movimiento → administranet_stock (MySQL transaccional)
     → Compras: remito → administranet_compras (MySQL transaccional)
     → MPR: Opt (PG) → orquesta movimientos en MySQL
```

### 2.3 Dependencias externas clave

| Dependencia | Versión | Uso |
|-------------|---------|-----|
| Django | 4.2 | Framework web |
| PostgreSQL | 13 | BD principal Synap |
| MySQL (externo) | 5.x/8.x | BD AdministraNET (charset latin1) |
| Redis | 6 | Cache (django-redis) |
| mysqlclient | 2.2.7 | Driver MySQL |
| django-tailwind | latest | CSS framework |
| DRF | latest | APIs REST |
| openpyxl / reportlab | latest | Exportación Excel/PDF |
| Pillow | 10.1.0 | Imágenes |
| whitenoise | 6.9.0 | Archivos estáticos en producción |
| Cloudflare | CDN | HTTPS, cache estáticos en producción |

---

## 3. Riesgos Técnicos Priorizados

### P1 — Críticos (impacto inmediato en operación/seguridad)

| # | Riesgo | Descripción | Impacto |
|---|--------|-------------|---------|
| 1.1 | **Clave AES hardcodeada** | `AES_KEY = b'a7v8xx2'` en `login/administranet_auth.py` y password MySQL por defecto en settings. | Compromiso de credenciales si el repo se expone. |
| 1.2 | **Caja sin MercadoPago** | Kioscos que operan sin módulo MercadoPago no registran movimientos en `caja` ni `caja_saldo`. | Ventas autoservicio sin registro contable; arqueos incorrectos. |
| 1.3 | **Archivos duplicados (* 2.py)** | En self_checkout hay 15+ archivos `* 2.py` (cart_service 2.py, confirmation_service 2.py, etc.). | Confusión, imports incorrectos, bugs difíciles de rastrear. |
| 1.4 | **Sin tests automatizados en CI** | No hay pipeline CI/CD visible; tests dependen de Docker manual. | Regresiones no detectadas; despliegues riesgosos. |
| 1.5 | **Usuario supervisor hardcodeado** | Permisos admin se otorgan por `cod_usuario == 'supervisor'`, no por rol. | No escalable; riesgo si se renombra o elimina. |

### P2 — Importantes (impacto a mediano plazo)

| # | Riesgo | Descripción | Impacto |
|---|--------|-------------|---------|
| 2.1 | **Charset mixto** | latin1 en pool MySQL y partes del código; utf8mb4 en sucursales. | Caracteres especiales corruptos o truncados. |
| 2.2 | **fe_afip huérfana** | App con código pero no instalada/registrada. | Confusión; espacio muerto; dependencia fantasma. |
| 2.3 | **query_runner monolítico** | `reports/services/query_runner.py` concentra toda la lógica SQL. | Difícil de testear, mantener y escalar reportes. |
| 2.4 | **Context processor pesado** | `usuario_y_permisos` hace múltiples consultas MySQL (empresa, sucursal, todas_sucursales) en cada request. | Latencia elevada en cada página; consultas N+1. |
| 2.5 | **Pool MySQL max_connections=5** | Pool limitado; "pool lleno" crea conexiones temporales sin límite. | Posible exhaustion de conexiones MySQL bajo carga. |
| 2.6 | **Mock objects en context** | `EmpresaMock`, `SucursalMock`, `LogoWrapper` definidos inline dentro del context processor. | Código frágil; no reutilizable; difícil de testear. |

### P3 — Menores (deuda técnica a planificar)

| # | Riesgo | Descripción |
|---|--------|-------------|
| 3.1 | Módulos fantasma en APPS_MENU y MODULE_CONFIGS (14+ no instalados) |
| 3.2 | Slug inconsistente en reportes (ventas_netas vs ventas-netas) |
| 3.3 | Documentación parcialmente obsoleta (LIMPIEZA_MODULOS, ADMINISTRANET_ANALYTICS) |
| 3.4 | `stock` no está en MODULE_CONFIGS pero sí instalada |
| 3.5 | `compras` y `mpr` no están en MODULE_CONFIGS |
| 3.6 | Firebase deshabilitado pero referencias en código |
| 3.7 | Backup dump de 1MB en raíz del repo (`synap_backup_20260122_1325.dump`) |
| 3.8 | Script `verify_mobile_optimizations.py` suelto en raíz |
| 3.9 | Entrypoint Docker borra y recrea migraciones de reports en cada arranque |
| 3.10 | Logging nivel DEBUG en producción (`'level': 'DEBUG'` en settings) |

---

## 4. Deuda Técnica y Quick Wins

### 4.1 Deuda técnica acumulada

| Área | Deuda | Severidad | Esfuerzo |
|------|-------|-----------|----------|
| **Archivos duplicados** | 15+ archivos `* 2.py` en self_checkout; decenas de `* 2.md`/`* 3.md` en docs/tablas | Alta | Bajo (1-2h) |
| **Mock objects inline** | EmpresaMock, SucursalMock, LogoWrapper creados dentro de context_processors | Media | Medio (4h) |
| **Pool MySQL sin límite real** | Cuando pool está lleno crea conexiones "temporales" sin ceiling | Media | Bajo (2h) |
| **Middleware custom en settings** | `custom_ajax_login_required` definido como función en settings.py | Baja | Bajo (30min) |
| **Tests insuficientes** | Pocos tests que golpeen MySQL; mayoría asume mocks o SQLite | Alta | Alto (semanas) |
| **SECRET_KEY insegura por defecto** | `default='insecure-placeholder'` en settings | Media | Bajo (5min) |
| **Dos bases = doble complejidad** | Migraciones, backups, transacciones cross-DB no soportadas nativamente | Alta | — (decisión arquitectónica) |
| **Servicios admin_* sin vistas** | core/services con 14 archivos de servicio; algunos sin UI expuesta | Media | Variable |
| **administranet_stock.py ~96KB** | Archivo de servicio monolítico | Media | Medio (refactor) |

### 4.2 Quick wins (alto impacto, bajo esfuerzo)

| # | Acción | Esfuerzo | Impacto |
|---|--------|----------|---------|
| QW1 | **Eliminar archivos `* 2.py` y `* 2.md`** en self_checkout y docs | 1h | Elimina confusión; reduce tamaño repo |
| QW2 | **Mover `custom_ajax_login_required` a `core/middleware/`** | 30min | Limpieza settings.py |
| QW3 | **Cambiar logging a WARNING en producción** | 15min | Reduce ruido en logs y mejora rendimiento |
| QW4 | **Eliminar dump de backup de raíz** | 5min | Repo más limpio; el dump no debe versionarse |
| QW5 | **Registrar stock, compras, mpr en MODULE_CONFIGS** | 1h | Coherencia entre registro y apps instaladas |
| QW6 | **Cachear empresa/sucursal en sesión** en vez de consultar MySQL por request | 4h | Reduce latencia significativamente |
| QW7 | **Extraer mocks a clases reutilizables** (ej. `core/dto.py`) | 3h | Código más limpio y testeable |
| QW8 | **Limpiar entradas APPS_MENU de módulos no instalados** | 2h | Menú sin ítems fantasma |
| QW9 | **Decidir sobre fe_afip**: activar o eliminar del repo | 30min | Reduce confusión |
| QW10 | **Agregar .gitignore para `*.dump`** | 5min | Evita volver a versionar dumps |

---

## 5. Preguntas Abiertas Críticas

| # | Pregunta | Contexto | Impacto de no responder |
|---|----------|----------|------------------------|
| Q1 | **¿Cuándo se reemplazará MySQL por PostgreSQL?** | docs/DEUDA_TECNICA_FASE1_MYSQL.md menciona "Fase 2 PostgreSQL" pero no hay timeline. | Doble BD indefinidamente; complejidad creciente. |
| Q2 | **¿Qué pasará con MercadoPago y caja?** | Caja solo funciona con MP instalado; ¿se extraerá la lógica de caja a un módulo independiente? | Kioscos sin caja operativa; reportes de caja incompletos. |
| Q3 | **¿Se activará fe_afip o se elimina?** | Código existente, no integrado. Self-checkout tiene servicios de FE. | Código muerto o funcionalidad necesaria bloqueada. |
| Q4 | **¿Cómo se escala a múltiples empresas?** | Modelo "una empresa por base MySQL"; PostgreSQL tiene un solo Empresa model. | Cada nueva empresa requiere crear una BD MySQL nueva. |
| Q5 | **¿Hay plan para CI/CD?** | No hay pipeline visible; tests se ejecutan manualmente en Docker. | Calidad incierta; deployments arriesgados. |
| Q6 | **¿Se mantiene VB6 en paralelo indefinidamente?** | Plan de migración Archivo por fases, pero >50 ítems siguen en VB6. | Doble mantenimiento; usuarios entre dos sistemas. |
| Q7 | **¿Quién consume Support (RAG)?** | Subproyecto independiente con su propio Docker; integra via API. | ¿Está en uso? ¿Se despliega junto a Synap? |
| Q8 | **¿Qué módulos comentados se reactivan pronto?** | 14+ apps comentadas (tiendanube, inventory, purchases, etc.). | MODULE_CONFIGS y APPS_MENU con referencias rotas. |
| Q9 | **¿Se necesita Celery a corto plazo?** | Comentado en settings; Redis existe pero solo para cache. | Tareas asíncronas (exportaciones largas, sync) no soportadas. |
| Q10 | **¿Quién mantiene el charset latin1?** | AdministraNET legacy; ¿se puede migrar a utf8mb4? | Problemas con caracteres especiales cada vez más frecuentes. |

---

## 6. Plan de Próximos 14 Días

### Semana 1 (Días 1-7): Estabilización y limpieza

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 1-2 | **QW1: Eliminar archivos duplicados** (`* 2.py`, `* 2.md`, `* 3.md`); **QW4: dump de raíz**; **QW10: .gitignore** | Dev | Repo limpio; commit en Desarrollo |
| 2-3 | **QW2: Mover middleware de settings**; **QW3: Logging a WARNING en prod** | Dev | settings.py más limpio |
| 3-4 | **QW5: Registrar stock/compras/mpr en MODULE_CONFIGS**; **QW8: Limpiar APPS_MENU** | Dev | Coherencia registro-apps |
| 4-5 | **QW6: Cachear empresa/sucursal en sesión** (evitar queries por request en context_processor) | Dev | Latencia reducida; medir con antes/después |
| 5-6 | **QW7: Extraer DTOs/Mocks** a `core/dto.py`; **QW9: Decidir fe_afip** | Dev + PO | Código más limpio; decisión documentada |
| 7 | **Actualizar documentación obsoleta** (LIMPIEZA_MODULOS, ADMINISTRANET_ANALYTICS, EVALUACION_DOCUMENTACION) | Dev | Docs alineados con estado real |

### Semana 2 (Días 8-14): Fundamentos para escalar

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 8-9 | **Responder Q2**: diseñar flujo de caja sin dependencia de MercadoPago | Arquitecto + PO | Doc de diseño en docs/general/ |
| 9-10 | **Primer pipeline CI básico**: lint (flake8/ruff) + `manage.py check` + tests unitarios existentes | DevOps | GitHub Actions o equivalente |
| 10-11 | **Refactor pool MySQL**: implementar ceiling real (queue con timeout en vez de crear conexiones ilimitadas) | Dev | Pool robusto; tests de carga |
| 11-12 | **Escribir tests de integración** para flujos críticos: login, alta de movimiento stock, confirmación self_checkout | Dev | Cobertura mínima de flujos transaccionales |
| 13 | **Definir roadmap migración Archivo** próximos 3 meses: priorizar Cliente y Proveedor | PO + Arquitecto | Roadmap en docs/general/ |
| 14 | **Review y retrospectiva**: validar que los quick wins mejoraron métricas; priorizar siguiente sprint | Equipo | Informe de sprint; backlog actualizado |

### Hitos clave

- **Día 3**: Repo sin archivos duplicados ni dumps; settings.py limpio.
- **Día 7**: MODULE_CONFIGS, APPS_MENU y documentación alineados con realidad.
- **Día 10**: Primer pipeline CI funcional.
- **Día 14**: Tests de integración para 3 flujos críticos; roadmap de migración definido.

---

## Anexo A: Inventario de Apps

| App | Instalada | En MODULE_CONFIGS | URLs | Directorio | Estado |
|-----|-----------|-------------------|------|------------|--------|
| core | Sí | Sí | Sí | Sí | Operativa |
| login | Sí | Sí | Sí | Sí | Operativa |
| dashboard | Sí | Sí | Redirect | Sí | Operativa |
| reports | Sí | Sí | Sí | Sí | Operativa (módulo más maduro) |
| self_checkout | Sí | Sí | Sí | Sí | Operativa (caja condicional) |
| stock | Sí | **No** | Sí | Sí | Operativa |
| compras | Sí | **No** | Sí | Sí | Operativa |
| mpr | Sí | **No** | Sí | Sí | En desarrollo |
| theme | Sí | No (UI) | No | Sí | Operativa |
| fe_afip | **No** | No | No | Sí | **Huérfana** |
| support | N/A | N/A | N/A | Sí (subproyecto) | Independiente |

## Anexo B: Mapa de tablas MySQL escritas por Synap

| Flujo | Tablas escritas |
|-------|----------------|
| Login/Sesión | sesion (INSERT/UPDATE) |
| Logout | sesion (UPDATE fechafin) |
| Self-Checkout confirmación | codmov, talonarios, cuentacliente, stock, stock_deposito, serie_entrada, resumen_venta_cv, tc_comprobante, self_checkout_cart, self_checkout_audit_log, caja*, caja_saldo* |
| Stock (alta movimiento) | codmov, talonarios, movimiento_stock, stock, stock_deposito, cuerpostock_mstock (temporal) |
| Compras (remito) | codmov, talonarios, movimiento_stock/stock, stockp, cuerpostock_mstock (temporal), comp_ped |
| MPR | lista_produccion_agrupada, lista_produccion_detalle, lista_produccion_historico, movimiento_stock, stock, stock_deposito, comp_ped (tipo_pedido_opt) |
| Datos empresa | DatosEmpresa, datosempresa2 |
| Sucursales | sucursales |
| Permisos sync | permiso_sistema, permiso_sistema_puesto |
| Punto de venta | punto_venta, reporte_comprobante |
| Cliente (parcial) | cliente (nombre_cliente desde self_checkout) |

*caja/caja_saldo: solo si módulo MercadoPago está instalado y configurado.

## Anexo C: Métricas de código (estimadas)

| Métrica | Valor |
|---------|-------|
| Apps Django propias instaladas | 8 |
| Servicios en core/services/ | 14 archivos |
| Archivo más grande (servicio) | administranet_stock.py (~96KB) |
| Vista más grande | core/views/views.py (~58KB) |
| Utils más grande | core/utils/utils.py (~50KB) |
| Documentos en /docs/ | 60+ archivos .md |
| Tablas documentadas en docs/general/tablas/ | 100+ |
| Archivos duplicados detectados (* 2.py) | ~15 en self_checkout |
| Módulos comentados en settings | 14 |
| Dependencias Python | 26 (requirements.txt) |

---

**Referencia:** Este informe se basa en la lectura de la documentación en `docs/`, el código fuente de todas las apps, la configuración Django (`settings.py`, `urls.py`), la infraestructura Docker y los scripts de despliegue. Debe actualizarse al completar cada sprint.
