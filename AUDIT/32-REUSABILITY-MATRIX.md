# 32 — Matriz de Reutilización

**Estado:** COMPLETE (Fase 32)  
**Fecha:** 25/08/2026

---

| Componente | Clasificación | Justificación |
|------------|:------------:|---------------|
| **core/mysql_pool** | REUSE WITH MINOR REFACTOR | Funcional; agregar interface |
| **core/module_registry + manager** | REUSE AS IS | Buen diseño modular |
| **core/url_registry** | REUSE AS IS | Funcional |
| **core/backup/** | REUSE WITH MINOR REFACTOR | Buen DR; abstraer fuentes |
| **core/administranet_stock** | REUSE WITH MAJOR REFACTOR | Mover a stock/ o ACL |
| **core/legacy_mysql_schema** | REUSE WITH MAJOR REFACTOR | Split por dominio |
| **login/administranet_auth** | REWRITE | Reemplazar con Identity service |
| **reports/models** | REUSE AS IS | Productizable |
| **reports/query_runner** | REWRITE | Monolito acoplado |
| **reports/execution_engine** | REUSE WITH MAJOR REFACTOR | Buena abstracción parcial |
| **reports/declarative-v1** | REUSE WITH MINOR REFACTOR | Builder genérico |
| **ia/models + llm_gateway** | REUSE AS IS | Framework IA productizable |
| **ecom/** (completo) | REUSE WITH MAJOR REFACTOR | 95 deps core + SQL |
| **mpr/** (completo) | REUSE WITH MAJOR REFACTOR | 44 deps core + 8000 LOC services |
| **self_checkout/** | REUSE WITH MAJOR REFACTOR | Pocos tests, SQL intenso |
| **fe_afip/** | REUSE AS IS | Bien encapsulado |
| **factura_compra_captura** | REUSE WITH MINOR REFACTOR | Buen diseño PG workflow |
| **tiendanube_administranet** | REUSE AS IS | Bien aislado |
| **odoo_migracion** | REUSE AS IS | Patrón adapter correcto |
| **legacy_db/repositories** | REUSE WITH MINOR REFACTOR | Buen patrón, extender |
| **theme/** | REUSE AS IS | UI framework |
| **support/** | REUSE AS IS | Ya separado |
| **dashboard/** (stub) | REMOVE | Reemplazado por core |
| **mtrix/** | REMOVE | Sin fuentes |
| **sia/** | REMOVE or ARCHIVE | No instalado |
| **mercadopago/** | REUSE WITH MAJOR REFACTOR | Si se reactiva |
| **pyafipws** | REUSE AS IS | Librería externa |
| **administranet_vb6/** | REMOVE from runtime | Solo referencia docs |

---

*Generado por auditoría READ ONLY.*
