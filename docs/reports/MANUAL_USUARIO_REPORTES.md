# Manual de usuario – Informes (Reports)

Guía práctica de los informes del módulo **Reports** orientados a marcas y licenciatarios (piloto Best Sox). Pensada para supervisores comerciales, gerencia y quien exporta reportes a marcas.

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar.

**Manual HTML en la app:** **`/reports/manual/`** (requiere sesión). Regenerar HTML: `python3 scripts/generar_manuales_html.py`.

**Fechas en pantalla:** siempre en formato **dd/MM/yyyy**.

### Filtros sucursal y punto de venta (familia BO de ventas)

En los informes de ventas con layout BO — **Objetivos vs BO**, **Ventas por vendedor**, **Ventas por artículo**, **Ventas por marca y SuperArt**, **Ventas BOM en docenas** y **Ventas marcas mensual** — el panel de filtros muestra selectores múltiples de **Sucursal** y **Punto de venta** (etiquetas). **Vacío = todos** los puntos de venta o sucursales.

El resumen del informe (encima de la tabla o KPIs) y el Excel indican **qué sucursales y qué puntos de venta** entran en el listado: nombres de las etiquetas elegidas, o **Todas** / **Todos** si no filtró.

**No** aparece el filtro Punto de venta en **BO vs stock vs facturación** (`bo-stock-facturacion`).

---

## 1. Acceso al módulo

1. En el menú de Synap, abra **Reports** (catálogo de informes).
2. Busque el informe por nombre o ábralo desde el **Command Center** (área Ventas), si tiene el atajo.
3. También puede pegar la URL directa del dashboard (ver cada informe más abajo).

Los informes de **artículos de venta** no incluyen ítems tipo **Gasto** (`articulo.tipo_art`). Eso aplica a marcas mensual, licenciatarios (tramo AdministraNET), SuperArt, ventas netas por artículo/rubro, utilidad gerencial y backorder.

### Idea clave

Hay informes hermanos que no se reemplazan:

| Informe | Para qué | ¿Datos históricos Excel? |
|---------|----------|---------------------------|
| **Ventas marcas mensual** | Análisis interno (matriz vendedor → cliente × mes) | No: solo AdministraNET |
| **Ventas por marca y SuperArt** | Jerarquía Marca → SuperArt → Artículo (packs, docenas, facturación) | No: solo AdministraNET |
| **Ventas BOM en docenas** | Componentes BOM con salida por venta (packs explosionados) | No: solo AdministraNET |
| **Ventas Mensuales Licenciatarios** | Armar el pack **Monthly Reporting** que se envía a marcas | Sí: seed + AdministraNET (híbrido) |

---

## 2. Ventas marcas mensual

**Nombre en catálogo:** Ventas marcas mensual.  
**URL:** `/reports/dashboard/ventas-marcas-mensual/`  
**Atajo:** `/reports/ventas-marcas-mensual/`

### Para qué sirve

Ver **ventas por marca** en una matriz: filas **Vendedor → Cliente**, columnas **mes**, celdas con **unidades** (packs o docenas) y **facturación**. La facturación del informe **incluye el descuento al pie de factura** aplicado en cabecera (neto post-pie por renglón). Incluye KPIs de regalías y tipo de cambio, comparación entre marcas y exportación Excel para uso interno.

No es el archivo que se manda a Levi’s / Puma / LW; para eso use **Ventas Mensuales Licenciatarios** (§3).

### Cómo usarlo

1. Abra el informe desde el catálogo o el Command Center.
2. Defina el **período de facturación** (desde–hasta).
3. Filtre por **marca**, **SuperArt**, **sucursal / punto de venta**, **clientes** y **vendedores** (incluir o excluir con etiquetas).
4. Elija **Packs** o **Docenas** según cómo quiera ver las unidades.
5. En **Licencia y proyección**, ajuste la **tasa de regalía (%)** (por defecto 13), el **TC** (si lo deja vacío usa la cotización vigente) y, si hace falta, active la **proyección** con su coeficiente (por defecto 1,07).
6. Pulse **Actualizar** para cargar datos (no se recargan solos al cambiar un filtro, salvo que tenga tiempo real activo).
7. Expanda o colapse vendedores en la matriz; el estado se recuerda en el navegador.
8. Exporte a Excel cuando lo necesite (hojas **Matriz** y **Detalle**).

### KPIs de cabecera

| KPI | Qué muestra |
|-----|-------------|
| Unidades / Docenas | Suma según el modo elegido |
| Facturación | Importe neto post-pie de renglón (FA / NC con signo, incluye descuento al pie) |
| Precio medio | Facturación ÷ unidades |
| Regalías | Facturación × tasa de regalía |
| Regalías / TC | Regalías convertidas (etiqueta USD) |

Los KPIs **no** aplican proyección: la proyección solo afecta la matriz y el detalle exportado.

### Proyección (opcional)

Con proyección activa, por cada celda:

- Unidades proyectadas = techo de (unidades × coeficiente)
- Monto proyectado = redondeo a 2 decimales de (facturación × coeficiente)

No es un forecast por días restantes del mes: es un coeficiente fijo sobre lo ya facturado.

### Preset SuperArt «Hombre»

- **Aplicar:** carga la lista de SuperArt guardada como preset Hombre.
- **Configurar** (solo supervisor): edita y guarda esa lista para la empresa.

### Comparar marcas

Puede comparar dos marcas (A y B) en el mismo período: KPIs y matriz con valores A/B y variación. En móvil, use las pestañas Marca A / Marca B. No elija la misma marca en A y B.

### Exportación Excel

- Hojas **Matriz** (pivot plano) y **Detalle** (renglón a renglón).
- En la primera hoja, bloque **Filtros aplicados** con sucursales y puntos de venta (nombres, o Todas/Todos).
- Columnas de nombre de vendedor y cliente (sin códigos).
- Si hay proyección, aparecen columnas de packs/docenas y monto proyectados.
- Nombre típico: `Ventas_marcas_mensual_{desde}_{hasta}.xlsx`.

### Problemas frecuentes

| Situación | Qué hacer |
|-----------|-----------|
| Las etiquetas de cliente/vendedor no buscan | Actualice la página (caché) y vuelva a abrir el informe; debe cargar catálogos de esta familia. |
| Matriz vacía con aviso de alcance | Su usuario no tiene vendedores en alcance o falló la validación; revise permisos comerciales. |
| Más de 24 meses en el período | La matriz muestra como máximo 24 meses recientes y avisa en pantalla. |
| Descarga bloqueada en Safari iOS | Siga el aviso de Synap para completar la descarga (no use diálogos del navegador). |

---

## 3. Ventas Mensuales Licenciatarios

**Nombre en catálogo:** Ventas Mensuales Licenciatarios.  
**URL:** `/reports/dashboard/ventas-mensuales-licenciatarios/`

### Para qué sirve

Preparar el **Monthly Reporting** que Best Sox envía a licenciatarios (Levi’s Bodywear/Legwear, LW propia, Puma, etc.): mismas hojas de negocio (`input Licensee sales`, `monthly`, regalía), no la matriz interna de §2.

### Cómo usarlo

1. Abra el informe desde Reports.
2. Pulse **Mostrar filtros**, elija **pack** y rango (mismo año calendario).
3. Opcional: filtre por **Sucursal** y/o **Punto de venta** (tags; vacío = todos). Estos filtros aplican **solo al tramo AdministraNET** (desde el 22/07/2026); el histórico importado del Excel (seed) no se recorta por sucursal/PV.
4. Opcional: en **Clientes a excluir**, busque y seleccione clientes AdministraNET; no aparecerán en la matriz, totales ni Excel exportado (tampoco filas seed vinculadas a esos códigos).
5. Pulse **Actualizar**. Verá la **matriz cliente × mes** (sin KPIs de cabecera) y una fila **Totales** al pie que suma cada columna; si busca un cliente, los totales reflejan las filas visibles.
6. Si el pack es **Puma** y hay SuperArt sin género en catálogo, el panel **Preview QA** listará los códigos y podrá pulsar **Clasificar SuperArt** (filtros o panel QA). En el modal Synap elija **Men** o **Women** por código; al guardar el contador baja y el código entra al catálogo activo.
7. En el banner, pulse **Exportar Excel** (icono de descarga, junto a Actualizar). El archivo usa la plantilla del pack (`input Licensee sales`, `monthly`, hoja QA) y una hoja **Filtros** al inicio con sucursales, puntos de venta y el resto de filtros aplicados.

### Packs previstos

| Pack | Línea (orientativo) | Unidad | Regalía típica |
|------|---------------------|--------|----------------|
| Levi’s Bodywear | BW | Docenas | 20 % |
| Levi’s Legwear (DZ) | LW | Docenas | 20 % |
| Levi’s Legwear (PK) | LW | Packs | 20 % |
| LW propia | LW | Docenas | 13 % |
| Puma Bodywear | Men BW | Packs | 13 % |
| Puma SW | Men/Women SW | Packs | 13 % |

### Qué no confundir

- Use **Ventas marcas mensual** para análisis diario/mensual interno y regalías estimadas en Synap.
- Use **este informe** para regenerar el archivo que se envía a la marca, con continuidad YTD tras el corte a AdministraNET.

Los **importes AdministraNET** (desde el 22/07/2026) incluyen el **descuento al pie de factura**, igual que Ventas marcas mensual. El histórico importado del Excel enviado no se recalcula.

---

## 4. Ventas por marca y SuperArt

**Nombre en catálogo:** Ventas por marca y SuperArt.  
**URL:** `/reports/dashboard/ventas-marca-superart/`  
**Atajo:** `/reports/ventas-marca-superart/`

### Para qué sirve

Ver ventas del período agrupadas por **Marca → SuperArt → Artículo**, con **Packs**, **Docenas** y **Facturación** en cada nivel. Útil para analizar el mix por marca y SuperArt sin la matriz mensual de VMM.

### Cómo usarlo

1. Abra el informe desde el catálogo.
2. Defina el **período de facturación**.
3. Opcionalmente filtre por **rubro / subrubro / marca**, **SuperArt**, sucursal, punto de venta, depósitos, clientes y vendedores.
4. Pulse **Actualizar**.
5. Expanda marcas y SuperArt para ver artículos; ordene por facturación, packs o docenas.
6. Exporte a Excel: archivo **plano** con columnas Marca | SuperArt | Articulo | Packs | Docenas | Facturacion.

### Problemas frecuentes

- **Sin datos:** revise período y filtros de marca/SuperArt; vacío en SuperArt = todos.
- **Docenas distintas a packs:** el factor depende de la U.M. del artículo (P1, P2, CU, etc.), igual que en Ventas marcas mensual.

---

## 5. Resumen rápido por rol

### Supervisor comercial

1. Abra **Ventas marcas mensual**, filtre marca/período y revise la matriz.
2. Ajuste tasa de regalía y TC si el escenario lo pide.
3. Exporte Matriz/Detalle para compartir internamente.
4. Use **Ventas Mensuales Licenciatarios** para el archivo que se envía a la marca.

### Gerencia / licencias

1. KPIs de regalías y regalías/TC en VMM para seguimiento interno.
2. En **Ventas Mensuales Licenciatarios**: elegir pack, período y **Exportar Excel** (plantilla Monthly Reporting).

### Administrador / operaciones

1. Mantenga migraciones y cotización TC al día.
2. Configure el preset Hombre (supervisor) si aplica.
3. Cuando existan planillas actualizadas, coordinar la carga de seed julio 01–21.

---

## 6. Clientes sin ventas por vendedor

**URL:** `/reports/dashboard/clientes-sin-ventas-vendedor/`

### Cómo usarlo

1. Elija **fecha desde** y **fecha hasta**.
2. Opcional: filtre por **Sucursal** y/o **Punto de venta** (tags; vacío = todos). Solo cuenta ventas en esas sucursales/PV para decidir si el cliente «tuvo ventas» en el período.
3. Opcional: restrinja **Vendedor** (gerencial) o use el alcance operativo de su sesión.
4. Pulse **Generar informe**.

Un cliente que facturó solo en otra sucursal puede aparecer como «sin ventas» al filtrar una sucursal concreta.

---

## 7. Ventas BOM en docenas

**Nombre en catálogo:** Ventas BOM en docenas.  
**URL:** `/reports/dashboard/ventas-bom-docenas/`  
**Atajo:** `/reports/ventas-bom-docenas/`

### Para qué sirve

Ver cuántos **artículos BOM (componentes)** salieron por venta facturada: cada pack vendido se explota según su lista de materiales. Unidades en **docenas** (pares ÷ 12) y **pares** de control. No muestra importe en pesos.

### Cómo usarlo

1. Defina el período de facturación.
2. Opcional: sucursal, PV, clientes, rubro/subrubro/marca del pack.
3. Pulse **Actualizar**.
4. Exporte a Excel si lo necesita.

---

## 8. Referencias técnicas

| Tema | Documento |
|------|-----------|
| Spec VMM | [SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md](SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md) |
| Spec Ventas por marca y SuperArt | [SPEC_INFORME_VENTAS_MARCA_SUPERART.md](SPEC_INFORME_VENTAS_MARCA_SUPERART.md) |
| Spec Ventas BOM en docenas | [SPEC_INFORME_VENTAS_BOM_DOCENAS.md](SPEC_INFORME_VENTAS_BOM_DOCENAS.md) |
| Spec VML | [SPEC_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md](SPEC_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md) |
| Análisis Monthly Reporting | [ANALISIS_MONTHLY_REPORTING_BEST_SOX_LICENCIATARIOS.md](ANALISIS_MONTHLY_REPORTING_BEST_SOX_LICENCIATARIOS.md) |
| Mapeo PuW/PuM | [MAPEO_PUW_PUM_ADMINISTRANET.md](MAPEO_PUW_PUM_ADMINISTRANET.md) |
| Smoke Best Sox VMM | [SMOKE_BEST_SOX_VMM.md](SMOKE_BEST_SOX_VMM.md) |

---

*Manual de usuario – Informes (Reports). Synap. Actualizado 31/08/2026.*
