# Diseño técnico: Informe «Ventas por marca y SuperArt»

Especificación: [`SPEC_INFORME_VENTAS_MARCA_SUPERART.md`](SPEC_INFORME_VENTAS_MARCA_SUPERART.md).

---

## Enfoque

Runner **dedicado** (`ventas_marca_superart_runner.py`), no flag en el monolito VO. Reutiliza signo FA/NC, factor docenas, **importe post-pie** (`sql_signo_imp_post_pie_expr` de VMM) y filtros catálogo `_vo_sql_filtros_articulo` de VO. UI clon conceptual de Ventas por artículo con columnas Packs/Docenas/Facturación.

---

## Decisiones

| Tema | Elección | Motivo |
|------|----------|--------|
| Runner | Dedicado | Jerarquía y métricas distintas a VPA; evita ensuciar VO |
| Factor U.M. | Import desde VMM | Un solo mapa P1/P2/… |
| Importe post-pie | `sql_signo_imp_post_pie_expr()` (VMM) | Paridad con Ventas marcas mensual y licenciatarios |
| Ajustes de cabecera | Marca sintética `codigo_marca=-1` «Ajustes sin mercadería» | Cierra el gap vs Ventas Netas (FA/NC sin renglón SuperArt vigente). Solo sin filtro de catálogo. UI itálica/ámbar, pin al pie. |
| JSON árbol | `meta.extra.tabs.marca_superart_jerarquia` | No acoplar a `objetivos_jerarquia` |
| Export | Plano 6 columnas | Pedido de producto; sin outline |
| SuperArt UI | IDs tags VMM (`vmm_superarts_incluidos`) | Reusar loader de tags en `dashboard.js` |

---

## Flujo

```text
Filtros → query_runner (vmsa_v1) → run_ventas_marca_superart
       → SQL GROUP BY marca + id_manual + artículo
       → (si no hay filtro catálogo) UNION lógica de FA/NC cabecera sin renglón SuperArt
       → _nest_marca_superart_articulo → jerarquía
       → _pin_ajustes_al_final → data[] flatten → UI / Excel
```

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `reports/services/ventas_marca_superart_runner.py` | SQL, nest, flatten, sort |
| `reports/services/ventas_marca_superart_seed.py` | ReportDefinition + ensure |
| `reports/migrations/0036_add_ventas_marca_superart_report.py` | Seed migrate |
| `reports/services/query_runner.py` | Dispatch + caché |
| `reports/services/export_service.py` | Headers / filename |
| `reports/static/reports/js/ventas_marca_superart.js` | Renderer jerárquico |
| `reports/templates/reports/dashboard_detail.html` | Shell + script |
| `reports/templates/reports/includes/filters_superart_tags.html` | Filtro SuperArt |

---

## Pruebas

`docker exec Synap_app python manage.py test reports.tests.test_ventas_marca_superart`
