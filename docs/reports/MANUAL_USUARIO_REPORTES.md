# Manual de usuario – Informes (Reports)

Guía práctica de los informes del módulo **Reports** orientados a marcas y licenciatarios (piloto Best Sox). Pensada para supervisores comerciales, gerencia y quien exporta reportes a marcas.

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar.

**Manual HTML en la app:** **`/reports/manual/`** (requiere sesión). Regenerar HTML: `python3 scripts/generar_manuales_html.py`.

**Fechas en pantalla:** siempre en formato **dd/MM/yyyy**.

---

## 1. Acceso al módulo

1. En el menú de Synap, abra **Reports** (catálogo de informes).
2. Busque el informe por nombre o ábralo desde el **Command Center** (área Ventas), si tiene el atajo.
3. También puede pegar la URL directa del dashboard (ver cada informe más abajo).

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

### Estado actual (fase 0)

El informe **ya figura en el catálogo** y abre el dashboard, pero la consulta aún responde **«en construcción»** (sin grilla ni export de plantilla). Las próximas fases cargarán:

1. **Seed** desde los Excel ya enviados (ene–jun congelados; julio 01–21 cuando lleguen las planillas actualizadas).
2. **AdministraNET** solo desde el **22/07/2026** en adelante.
3. **Julio total** = seed (01–21) + AdministraNET (22–31).
4. Export Excel con el formato de plantilla de cada pack.

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
- Use **este informe** (cuando esté operativo) para regenerar el archivo que se envía a la marca, con continuidad YTD tras el corte a AdministraNET.

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
4. No use aún Licenciatarios para envíos reales (fase 0).

### Gerencia / licencias

1. KPIs de regalías y regalías/TC en VMM para seguimiento interno.
2. Cuando VML esté listo: elegir pack, período y exportar plantilla Monthly Reporting.

### Administrador / operaciones

1. Mantenga migraciones y cotización TC al día.
2. Configure el preset Hombre (supervisor) si aplica.
3. Cuando existan planillas actualizadas, coordinar la carga de seed julio 01–21.

---

## 6. Ventas BOM en docenas

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

## 7. Referencias técnicas

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

*Manual de usuario – Informes (Reports). Synap. Actualizado 14/08/2026.*
