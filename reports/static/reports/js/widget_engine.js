/**
 * Widget Engine - Motor genérico para renderizar widgets de reportes declarativos
 * 
 * Este módulo permite renderizar widgets automáticamente basándose en schemas
 * de reportes declarativos, sin necesidad de código específico por reporte.
 */

const WidgetEngine = {
  /**
   * Inicializa el motor de widgets en un elemento raíz
   * @param {HTMLElement} rootElement - Elemento contenedor
   * @param {Object} schema - Schema del reporte
   * @param {Object} queryResult - Resultado de la consulta (meta, data, totals, notes)
   */
  init(rootElement, schema, queryResult, reportSlug = null) {
    if (!rootElement || !schema || !queryResult) {
      console.error("WidgetEngine.init: parámetros requeridos faltantes");
      return;
    }

    this.rootElement = rootElement;
    this.schema = schema;
    this.queryResult = queryResult;
    this.widgets = new Map();
    this.reportSlug = reportSlug; // Almacenar el slug del reporte para usar en renderizado

    return this;
  },

  /** Clave localStorage para campos de agrupación de tabla (por reporte y widget). */
  _tableGroupingStorageKey(slug, widgetId) {
    if (!slug || widgetId == null || widgetId === "") return null;
    return `report_table_grouping_v1_${slug}_${String(widgetId)}`;
  },

  /**
   * Lee estado guardado. `used: true` si existía clave (incluso fields vacío = usuario eligió sin agrupar).
   */
  _loadTableGroupingStorageState(slug, widgetId) {
    const key = this._tableGroupingStorageKey(slug, widgetId);
    if (!key || typeof localStorage === "undefined") {
      return { used: false, fields: [] };
    }
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return { used: false, fields: [] };
      const parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.fields)) return { used: true, fields: [] };
      return { used: true, fields: parsed.fields };
    } catch (e) {
      return { used: false, fields: [] };
    }
  },

  _savePersistedTableGrouping(slug, widgetId, fields) {
    const key = this._tableGroupingStorageKey(slug, widgetId);
    if (!key || typeof localStorage === "undefined") return;
    try {
      const list = Array.isArray(fields) ? fields : [];
      localStorage.setItem(key, JSON.stringify({ fields: list }));
    } catch (e) {
      /* cuota o modo privado */
    }
  },

  /**
   * Renderiza el dashboard completo con todos los widgets por defecto
   * @param {HTMLElement} rootElement - Elemento contenedor (opcional, usa this.rootElement si no se proporciona)
   */
  renderDefaultDashboard(rootElement = null) {
    const container = rootElement || this.rootElement;
    if (!container || !this.schema) {
      console.error("WidgetEngine.renderDefaultDashboard: schema o contenedor faltante");
      return;
    }

    // Limpiar contenedor
    container.innerHTML = "";

    // Renderizar cada widget por defecto
    const defaultWidgets = this.schema.default_widgets || [];
    
    console.log(`[WidgetEngine] Renderizando ${defaultWidgets.length} widgets en contenedor:`, {
      containerClasses: container.className,
      containerStyle: container.style.cssText,
      containerHeight: container.offsetHeight,
      containerWidth: container.offsetWidth,
      containerDisplay: window.getComputedStyle(container).display,
      containerVisibility: window.getComputedStyle(container).visibility,
      containerOpacity: window.getComputedStyle(container).opacity
    });
    
    defaultWidgets.forEach((widgetSchema, index) => {
      const widgetElement = this.createWidgetContainer(widgetSchema, index);
      
      // Asegurar que el widget sea visible
      widgetElement.style.display = "block";
      widgetElement.style.visibility = "visible";
      widgetElement.style.opacity = "1";
      widgetElement.style.width = "100%";
      
      container.appendChild(widgetElement);
      
      // Forzar un reflow antes de renderizar
      void widgetElement.offsetWidth;
      
      this.renderWidget(widgetElement, widgetSchema);
      
      // Verificar después de renderizar
      const contentElement = widgetElement.querySelector("[data-widget-content]");
      if (contentElement) {
        console.log(`[WidgetEngine] Widget ${index} después de renderizar:`, {
          widgetHeight: widgetElement.offsetHeight,
          widgetWidth: widgetElement.offsetWidth,
          contentHeight: contentElement.offsetHeight,
          contentWidth: contentElement.offsetWidth,
          svg: contentElement.querySelector("svg") ? {
            width: contentElement.querySelector("svg").getAttribute("width"),
            height: contentElement.querySelector("svg").getAttribute("height"),
            display: window.getComputedStyle(contentElement.querySelector("svg")).display
          } : null
        });
      }
    });

    // Si no hay widgets, mostrar mensaje
    if (defaultWidgets.length === 0) {
      container.innerHTML = `
        <div class="rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 p-12 text-center">
          <p class="text-sm text-slate-500 dark:text-slate-400">No hay widgets configurados para este reporte.</p>
        </div>
      `;
    } else {
      // Verificar que los widgets se hayan creado correctamente
      const createdWidgets = container.querySelectorAll("[data-widget-id]");
      console.log(`[WidgetEngine] Widgets creados: ${createdWidgets.length}, esperados: ${defaultWidgets.length}`);
      createdWidgets.forEach((w, i) => {
        console.log(`[WidgetEngine] Widget ${i}:`, {
          id: w.getAttribute("data-widget-id"),
          kind: w.getAttribute("data-widget-kind"),
          height: w.offsetHeight,
          width: w.offsetWidth,
          visible: w.offsetHeight > 0 && w.offsetWidth > 0
        });
      });
    }
  },

  /**
   * Crea un contenedor HTML para un widget
   * @param {Object} widgetSchema - Schema del widget
   * @param {number} index - Índice del widget
   * @returns {HTMLElement} Elemento contenedor
   */
  createWidgetContainer(widgetSchema, index) {
    const container = document.createElement("div");
    // Para workspace, usar estilos más compactos sin márgenes grandes
    // Detectar si estamos en workspace (verificar desde rootElement o desde el contenedor)
    const isWorkspace = this.rootElement?.closest("[data-workspace-mode]") || 
                        this.rootElement?.hasAttribute("data-workspace-mode") ||
                        container?.closest("[data-workspace-mode]") ||
                        document.querySelector("[data-workspace-mode]");
    const isVentasNetas = this.reportSlug === "ventas-netas";
    // En workspace, SIEMPRE ocultar el header del widget (ya existe el header del workspace)
    const shouldHideTitle = isWorkspace;
    
    // En workspace, NO agregar bordes, sombras ni fondos adicionales (el widget del workspace ya los tiene)
    // Solo agregar clases necesarias para el layout interno
    if (isWorkspace) {
      // En workspace, el contenedor debe ser transparente y sin bordes/sombras
      // El widget del workspace ya tiene su propio contenedor con estilos
      container.className = "w-full h-full overflow-hidden";
    } else {
      // Fuera de workspace, usar estilos completos con bordes y sombras
      if (isVentasNetas) {
        container.className = "rounded-2xl border border-transparent bg-white dark:bg-slate-950 shadow-lg shadow-slate-900/5 overflow-hidden transition-all duration-500 hover:-translate-y-1 mb-6";
      } else {
        container.className = "rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-lg shadow-slate-900/5 overflow-hidden transition-all duration-500 hover:-translate-y-1 mb-6";
      }
    }
    container.setAttribute("data-widget-id", widgetSchema.id);
    container.setAttribute("data-widget-kind", widgetSchema.kind);

    const header = document.createElement("header");
    // Si no hay título ni botón (ventas_netas en workspace), ocultar completamente el header
    if (shouldHideTitle) {
      header.className = "hidden"; // Ocultar completamente el header
    } else {
      header.className = "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0 px-4 sm:px-6 py-3 sm:py-4 border-b border-slate-100 dark:border-slate-800";
    }

    // Solo mostrar el título si no es ventas_netas en workspace (es redundante con el título del widget)
    if (!shouldHideTitle) {
      const titleDiv = document.createElement("div");
      const title = document.createElement("h2");
      // En workspace, usar tamaño más pequeño para el título
      title.className = isWorkspace 
        ? "text-xs font-semibold text-slate-900 dark:text-white"
        : "text-xs sm:text-sm font-semibold text-slate-900 dark:text-white";
      
      // Si es una tabla y tiene configuración de título con conteo/métricas, construir título dinámico
      // En workspace, SIEMPRE usar el título dinámico para tablas (reemplaza el título estático)
      let titleText = widgetSchema.title || "Widget";
      if (widgetSchema.kind === "table" && this.queryResult?.data) {
        const dynamicTitle = this.buildTableTitle(widgetSchema, this.queryResult.data);
        if (dynamicTitle) {
          // En workspace, el título dinámico reemplaza completamente el título estático
          titleText = isWorkspace ? dynamicTitle : (dynamicTitle || widgetSchema.title || "Widget");
        } else if (isWorkspace) {
          // Si no hay título dinámico pero estamos en workspace, usar el título base con conteo
          const count = this.queryResult.data.length;
          titleText = `${widgetSchema.title || "Widget"} ${count}`;
        }
      }
      
      // Si el título contiene HTML (badge), usar innerHTML, sino textContent
      if (titleText.includes("<span") || titleText.includes("<div")) {
        title.innerHTML = titleText;
      } else {
        title.textContent = titleText;
      }
      
      titleDiv.appendChild(title);

      if (widgetSchema.description) {
        const description = document.createElement("p");
        description.className = "text-[10px] sm:text-xs text-slate-500 dark:text-slate-400 mt-1";
        description.textContent = widgetSchema.description;
        titleDiv.appendChild(description);
      }

      header.appendChild(titleDiv);
    }

    // Acciones (toggle tabla y personalizar colores) - solo para gráficos (bar, line, area)
    // El botón se crea solo si el widget es un gráfico que puede mostrar tabla
    // PERO NO para ventas_netas en workspace (no debe mostrarse según requerimiento)
    const widgetKind = widgetSchema.kind;
    const shouldShowTableToggle = ['bar', 'line', 'area'].includes(widgetKind) && !(isWorkspace && isVentasNetas);
    const canHaveSeries = ['bar', 'line'].includes(widgetKind) && widgetSchema.series_dimension;
    
    if (shouldShowTableToggle || canHaveSeries) {
      const actionsDiv = document.createElement("div");
      actionsDiv.className = "flex items-center gap-2 text-[11px]";
      
      // Botón de personalizar colores (solo para gráficos con series)
      if (canHaveSeries) {
        const colorBtn = document.createElement("button");
        colorBtn.type = "button";
        colorBtn.dataset.customizeColors = "";
        colorBtn.className = "inline-flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-semibold text-purple-500 hover:text-purple-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-purple-400 rounded-full px-2.5 sm:px-3 py-1 transition";
        colorBtn.innerHTML = `
          <svg class="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M7 21a4 4 0 0 1-4-4V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v12a4 4 0 0 1-4 4Zm0 0h12a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 0 1 2.828 0l2.829 2.829a2 2 0 0 1 0 2.828l-8.486 8.485M7 17h.01" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="hidden sm:inline">Colores</span>
        `;
        colorBtn.title = "Personalizar colores de las series";
        actionsDiv.appendChild(colorBtn);
      }
      
      // Botón de toggle tabla
      if (shouldShowTableToggle) {
      const toggleBtn = document.createElement("button");
      toggleBtn.type = "button";
      toggleBtn.dataset.toggleTable = "";
      toggleBtn.className = "inline-flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-semibold text-sky-500 hover:text-sky-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-sky-400 rounded-full px-2.5 sm:px-3 py-1 transition";
      toggleBtn.innerHTML = `
        <svg class="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M4 5h16M4 10h16M4 15h16M4 20h10" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="hidden sm:inline">Ver tabla</span>
      `;
      actionsDiv.appendChild(toggleBtn);
      }
      
      header.appendChild(actionsDiv);
    }
    
    container.appendChild(header);

    const content = document.createElement("div");
    content.className = "relative";
    content.setAttribute("data-widget-content", "");
    container.appendChild(content);

    // Wrapper de tabla (oculto por defecto) - solo para gráficos que pueden mostrar tabla
    // NO crear el wrapper para ventas_netas en workspace (no debe permitirse ver la tabla)
    if (shouldShowTableToggle) {
      const tableWrapper = document.createElement("div");
      tableWrapper.className = "p-4 sm:p-6 hidden";
      tableWrapper.setAttribute("data-widget-table-wrapper", "");
      container.appendChild(tableWrapper);
    }

    return container;
  },

  /**
   * Renderiza un widget específico según su tipo
   * @param {HTMLElement} widgetElement - Elemento contenedor del widget
   * @param {Object} widgetSchema - Schema del widget
   */
  renderWidget(widgetElement, widgetSchema) {
    const contentElement = widgetElement.querySelector("[data-widget-content]");
    if (!contentElement) {
      console.error("WidgetEngine.renderWidget: elemento de contenido no encontrado");
      return;
    }

    switch (widgetSchema.kind) {
      case "kpi":
        this.renderKPI(contentElement, widgetSchema);
        break;
      case "bar":
        this.renderBarChart(contentElement, widgetSchema);
        // Solo adjuntar toggle de tabla si el botón existe (no se crea para ventas_netas en workspace)
        if (widgetElement.querySelector("[data-toggle-table]")) {
          this.attachTableToggle(widgetElement, widgetSchema);
        }
        // Adjuntar panel de personalización de colores si el botón existe
        if (widgetElement.querySelector("[data-customize-colors]")) {
          this.attachColorCustomizer(widgetElement, widgetSchema);
        }
        break;
      case "line":
        this.renderLineChart(contentElement, widgetSchema);
        // Solo adjuntar toggle de tabla si el botón existe (no se crea para ventas_netas en workspace)
        if (widgetElement.querySelector("[data-toggle-table]")) {
          this.attachTableToggle(widgetElement, widgetSchema);
        }
        // Adjuntar panel de personalización de colores si el botón existe
        if (widgetElement.querySelector("[data-customize-colors]")) {
          this.attachColorCustomizer(widgetElement, widgetSchema);
        }
        break;
      case "table":
        this.renderTable(contentElement, widgetSchema);
        // Ocultar botón de tabla en widgets que ya son tabla
        const toggleBtn = widgetElement.querySelector("[data-toggle-table]");
        if (toggleBtn) toggleBtn.classList.add("hidden");
        break;
      default:
        contentElement.innerHTML = `<p class="p-4 text-sm text-slate-500">Tipo de widget no soportado: ${widgetSchema.kind}</p>`;
    }
  },

  /**
   * Toggle tabla para widgets de gráfico
   */
  attachTableToggle(container, widgetSchema) {
    const toggleButton = container.querySelector("[data-toggle-table]");
    const tableWrapper = container.querySelector("[data-widget-table-wrapper]");
    if (!toggleButton || !tableWrapper) return;

    // El gráfico siempre debe estar visible, no lo tocamos
    const chartContent = container.querySelector("[data-widget-content]");

    const setButtonLabel = (showTable) => {
      toggleButton.innerHTML = showTable
        ? `
          <svg class="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M4 5h16M4 10h16M4 15h16M8 20h8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="hidden sm:inline">Ocultar tabla</span>
        `
        : `
          <svg class="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M4 5h16M4 10h16M4 15h16M4 20h10" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="hidden sm:inline">Ver tabla</span>
        `;
    };

    // Estado inicial: tabla oculta, gráfico visible (gráfico siempre visible)
    setButtonLabel(false);
    tableWrapper.classList.add("hidden");
    // Asegurar que el gráfico esté visible
    if (chartContent) chartContent.classList.remove("hidden");

    // Prevenir múltiples event listeners
    const newToggleButton = toggleButton.cloneNode(true);
    toggleButton.parentNode.replaceChild(newToggleButton, toggleButton);
    
    newToggleButton.onclick = () => {
      const currentTableWrapper = container.querySelector("[data-widget-table-wrapper]");
      if (!currentTableWrapper) {
        console.error("No se encontró el contenedor de la tabla");
        return;
      }
      
      const isTableHidden = currentTableWrapper.classList.contains("hidden");
      if (isTableHidden) {
        // Mostrar tabla (el gráfico permanece visible)
        // Limpiar el contenido previo para evitar duplicados
        currentTableWrapper.innerHTML = "";
        this.renderTable(currentTableWrapper, widgetSchema);
        currentTableWrapper.classList.remove("hidden");
        // NO ocultar el gráfico - debe permanecer visible
        setButtonLabel(true); // Cambiar a "Ocultar tabla"
      } else {
        // Ocultar tabla (el gráfico permanece visible)
        currentTableWrapper.classList.add("hidden");
        // NO tocar el gráfico - debe permanecer visible
        setButtonLabel(false); // Cambiar a "Ver tabla"
      }
    };
  },

  /**
   * Panel lateral para personalizar colores de las series del gráfico
   * @param {HTMLElement} container - Contenedor del widget
   * @param {Object} widgetSchema - Schema del widget
   */
  attachColorCustomizer(container, widgetSchema) {
    const customizeButton = container.querySelector("[data-customize-colors]");
    if (!customizeButton) return;

    // Obtener las series del gráfico
    const seriesDimension = widgetSchema.series_dimension;
    if (!seriesDimension) return;

    const data = this.queryResult.data || [];
    const seriesValues = [...new Set(data.map(d => String(d[seriesDimension] || 'Sin serie').trim()))].sort();
    
    if (seriesValues.length === 0) return;

    // Crear panel lateral
    const panel = document.createElement("div");
    panel.className = "fixed inset-y-0 right-0 w-80 sm:w-96 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-2xl z-50 transform translate-x-full transition-transform duration-300 ease-in-out";
    panel.setAttribute("data-color-panel", "");
    panel.innerHTML = `
      <div class="flex flex-col h-full">
        <!-- Header del panel -->
        <div class="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h3 class="text-sm font-semibold text-slate-900 dark:text-white">Personalizar Colores</h3>
          <button type="button" data-close-color-panel class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M18 6L6 18M6 6l12 12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
        
        <!-- Contenido del panel -->
        <div class="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
          <p class="text-xs text-slate-500 dark:text-slate-400 mb-4">Selecciona un color para cada serie del gráfico. Los cambios se aplicarán automáticamente.</p>
          
          <div class="space-y-3" data-color-list>
            <!-- Las series se agregarán aquí dinámicamente -->
          </div>
        </div>
        
        <!-- Footer con botones de acción -->
        <div class="px-4 sm:px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex gap-2">
          <button type="button" data-reset-colors class="flex-1 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors">
            Restaurar
          </button>
          <button type="button" data-close-color-panel class="flex-1 px-3 py-2 text-xs font-medium text-white bg-sky-600 hover:bg-sky-700 rounded-lg transition-colors">
            Cerrar
          </button>
        </div>
      </div>
    `;

    // Agregar panel al body
    document.body.appendChild(panel);

    // Obtener colores guardados desde localStorage o configuración
    const widgetId = container.getAttribute("data-widget-id");
    const storageKey = `widget_colors_${widgetId}`;
    const savedColors = this.getSavedColors(widgetId, widgetSchema);
    const savedTextColors = this.getSavedTextColors(widgetId, widgetSchema);
    const savedFontSizes = this.getSavedFontSizes(widgetId, widgetSchema);
    
    // Renderizar lista de series con selectores de color y tamaño de fuente
    const colorList = panel.querySelector("[data-color-list]");
    seriesValues.forEach((series, index) => {
      const defaultColors = ["#8b5cf6", "#06b6d4", "#f59e0b", "#10b981", "#ef4444", "#3b82f6"];
      const currentColor = savedColors[series] || defaultColors[index % defaultColors.length];
      
      // Color de texto por defecto: blanco para fondos oscuros, negro para claros
      const isDarkColor = this.isColorDark(currentColor);
      const defaultTextColor = isDarkColor ? "#ffffff" : "#1e293b";
      const currentTextColor = savedTextColors[series] || defaultTextColor;
      
      // Tamaño de fuente por defecto: 9px para textos dentro de barras
      const defaultFontSize = 9;
      const currentFontSize = savedFontSizes[series] || defaultFontSize;
      
      const seriesItem = document.createElement("div");
      seriesItem.className = "flex flex-col gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50";
      seriesItem.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="flex-1">
            <div class="text-xs font-medium text-slate-900 dark:text-white mb-1">${series}</div>
            <div class="text-[10px] text-slate-500 dark:text-slate-400">Serie ${index + 1}</div>
          </div>
        </div>
        <div class="flex flex-col gap-3">
          <div class="flex items-center gap-3">
            <div class="flex-1">
              <label class="block text-[10px] font-medium text-slate-600 dark:text-slate-400 mb-1.5">Color de fondo</label>
              <div class="flex items-center gap-2">
                <div class="w-8 h-8 rounded border-2 border-slate-300 dark:border-slate-600" style="background-color: ${currentColor}" data-color-preview></div>
                <input type="color" value="${currentColor}" data-series="${series}" data-color-type="background"
                       class="w-10 h-8 rounded border border-slate-300 dark:border-slate-600 cursor-pointer" 
                       title="Seleccionar color de fondo para ${series}">
              </div>
            </div>
            <div class="flex-1">
              <label class="block text-[10px] font-medium text-slate-600 dark:text-slate-400 mb-1.5">Color de texto</label>
              <div class="flex items-center gap-2">
                <div class="w-8 h-8 rounded border-2 border-slate-300 dark:border-slate-600 flex items-center justify-center" style="background-color: ${currentTextColor}" data-text-color-preview>
                  <span class="text-[10px] font-bold" style="color: ${currentTextColor === '#ffffff' || currentTextColor === '#fff' ? '#1e293b' : '#ffffff'}">Aa</span>
                </div>
                <input type="color" value="${currentTextColor}" data-series="${series}" data-color-type="text"
                       class="w-10 h-8 rounded border border-slate-300 dark:border-slate-600 cursor-pointer" 
                       title="Seleccionar color de texto para ${series}">
              </div>
            </div>
          </div>
          <div class="flex-1">
            <label class="block text-[10px] font-medium text-slate-600 dark:text-slate-400 mb-1.5">Tamaño de fuente (px)</label>
            <div class="flex items-center gap-2">
              <input type="range" min="6" max="20" step="1" value="${currentFontSize}" 
                     data-series="${series}" data-font-size-input
                     class="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500">
              <input type="number" min="6" max="20" step="1" value="${currentFontSize}" 
                     data-series="${series}" data-font-size-number
                     class="w-16 px-2 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white">
            </div>
          </div>
        </div>
      `;
      colorList.appendChild(seriesItem);
    });

    // Event listeners
    const closeButtons = panel.querySelectorAll("[data-close-color-panel]");
    closeButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        panel.classList.add("translate-x-full");
        setTimeout(() => panel.remove(), 300);
      });
    });

    const resetButton = panel.querySelector("[data-reset-colors]");
    resetButton.addEventListener("click", () => {
      // Restaurar colores y tamaños por defecto
      localStorage.removeItem(storageKey);
      localStorage.removeItem(`widget_text_colors_${widgetId}`);
      localStorage.removeItem(`widget_font_sizes_${widgetId}`);
      // Recargar el gráfico
      const widgetKind = widgetSchema.kind;
      if (widgetKind === "bar") {
        this.renderBarChart(container.querySelector("[data-widget-content]"), widgetSchema);
      } else if (widgetKind === "line") {
        this.renderLineChart(container.querySelector("[data-widget-content]"), widgetSchema);
      }
      panel.classList.add("translate-x-full");
      setTimeout(() => panel.remove(), 300);
    });

    // Cambios de color en tiempo real
    const colorInputs = panel.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
      input.addEventListener("input", (e) => {
        const series = e.target.dataset.series;
        const colorType = e.target.dataset.colorType; // "background" o "text"
        const newColor = e.target.value;
        
        if (colorType === "background") {
          // Actualizar preview de color de fondo
          const preview = e.target.closest(".flex").querySelector("[data-color-preview]");
          if (preview) {
            preview.style.backgroundColor = newColor;
          }
          
          // Guardar color de fondo
          const currentColors = this.getSavedColors(widgetId, widgetSchema);
          currentColors[series] = newColor;
          this.saveColors(widgetId, currentColors);
          
          // Aplicar color al gráfico en tiempo real
          this.applyColorToChart(container, series, newColor, widgetSchema);
          
          // Si no hay color de texto personalizado, sugerir uno basado en el nuevo color de fondo
          const currentTextColors = this.getSavedTextColors(widgetId, widgetSchema);
          if (!currentTextColors[series]) {
            const suggestedTextColor = this.isColorDark(newColor) ? "#ffffff" : "#1e293b";
            const textInput = e.target.closest(".flex").querySelector('input[data-color-type="text"]');
            if (textInput) {
              textInput.value = suggestedTextColor;
              // Actualizar preview de texto
              const textPreview = e.target.closest(".flex").querySelector("[data-text-color-preview]");
              if (textPreview) {
                textPreview.style.backgroundColor = suggestedTextColor;
                const textSpan = textPreview.querySelector("span");
                if (textSpan) {
                  textSpan.style.color = this.isColorDark(suggestedTextColor) ? "#ffffff" : "#1e293b";
                }
              }
            }
          }
        } else if (colorType === "text") {
          // Actualizar preview de color de texto
          const textPreview = e.target.closest(".flex").querySelector("[data-text-color-preview]");
          if (textPreview) {
            textPreview.style.backgroundColor = newColor;
            const textSpan = textPreview.querySelector("span");
            if (textSpan) {
              // Invertir el color del texto "Aa" para que sea visible
              textSpan.style.color = this.isColorDark(newColor) ? "#ffffff" : "#1e293b";
            }
          }
          
          // Guardar color de texto
          const currentTextColors = this.getSavedTextColors(widgetId, widgetSchema);
          currentTextColors[series] = newColor;
          this.saveTextColors(widgetId, currentTextColors);
          
          // Aplicar color de texto al gráfico en tiempo real
          this.applyTextColorToChart(container, series, newColor, widgetSchema);
        }
      });
    });

    // Cambios de tamaño de fuente en tiempo real
    const fontSizeInputs = panel.querySelectorAll('[data-font-size-input], [data-font-size-number]');
    fontSizeInputs.forEach(input => {
      input.addEventListener("input", (e) => {
        const series = e.target.dataset.series;
        const newFontSize = parseInt(e.target.value);
        
        // Validar rango
        if (newFontSize < 6 || newFontSize > 20) return;
        
        // Sincronizar ambos inputs (range y number)
        const seriesItem = e.target.closest('[class*="flex flex-col"]');
        if (seriesItem) {
          const rangeInput = seriesItem.querySelector('[data-font-size-input]');
          const numberInput = seriesItem.querySelector('[data-font-size-number]');
          if (rangeInput && numberInput) {
            if (e.target === rangeInput) {
              numberInput.value = newFontSize;
            } else {
              rangeInput.value = newFontSize;
            }
          }
        }
        
        // Guardar tamaño de fuente
        const currentFontSizes = this.getSavedFontSizes(widgetId, widgetSchema);
        currentFontSizes[series] = newFontSize;
        this.saveFontSizes(widgetId, currentFontSizes);
        
        // Aplicar tamaño de fuente al gráfico en tiempo real
        this.applyFontSizeToChart(container, series, newFontSize, widgetSchema);
      });
    });

    // Cerrar al hacer clic fuera del panel
    const overlay = document.createElement("div");
    overlay.className = "fixed inset-0 bg-black/20 dark:bg-black/40 z-40 opacity-0 pointer-events-none transition-opacity duration-300";
    overlay.setAttribute("data-color-overlay", "");

    // Abrir panel al hacer clic en el botón
    customizeButton.addEventListener("click", () => {
      document.body.appendChild(overlay);
      document.body.appendChild(panel);
      setTimeout(() => {
        overlay.classList.remove("opacity-0");
        overlay.classList.add("opacity-100");
        overlay.classList.remove("pointer-events-none");
      }, 10);
      panel.classList.remove("translate-x-full");
    });

    overlay.addEventListener("click", () => {
      panel.classList.add("translate-x-full");
      overlay.classList.add("opacity-0");
      overlay.classList.add("pointer-events-none");
      setTimeout(() => {
        overlay.remove();
        panel.remove();
      }, 300);
    });
  },

  /**
   * Obtiene los colores guardados para un widget
   */
  getSavedColors(widgetId, widgetSchema) {
    const storageKey = `widget_colors_${widgetId}`;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn("Error cargando colores guardados:", e);
    }
    
    // Si hay colores en la configuración del widget, usarlos
    return widgetSchema.color_mapping || {};
  },

  /**
   * Guarda los colores personalizados
   */
  saveColors(widgetId, colors) {
    const storageKey = `widget_colors_${widgetId}`;
    try {
      localStorage.setItem(storageKey, JSON.stringify(colors));
    } catch (e) {
      console.warn("Error guardando colores:", e);
    }
  },

  /**
   * Aplica un color a una serie específica del gráfico en tiempo real
   */
  applyColorToChart(container, seriesName, color, widgetSchema) {
    const contentElement = container.querySelector("[data-widget-content]");
    if (!contentElement) return;

    const svg = contentElement.querySelector("svg");
    if (!svg) return;

    // Buscar todos los elementos de la serie (rects, paths, etc.)
    const seriesElements = svg.querySelectorAll(`[data-series="${seriesName}"]`);
    
    seriesElements.forEach(element => {
      // Para gráficos apilados con degradados, actualizar el gradiente
      const fillAttr = element.getAttribute("fill");
      if (fillAttr && fillAttr.startsWith("url(#gradient-")) {
        // Actualizar el gradiente SVG
        const gradientId = fillAttr.match(/url\(#gradient-(\d+)\)/)?.[1];
        if (gradientId) {
          const gradient = svg.querySelector(`#gradient-${gradientId}`);
          if (gradient) {
            // Crear un degradado más oscuro para el final
            const darkerColor = this.darkenColor(color, 0.2);
            const stops = gradient.querySelectorAll("stop");
            if (stops.length >= 2) {
              stops[0].setAttribute("stop-color", color);
              stops[1].setAttribute("stop-color", darkerColor);
            }
          }
        }
      } else {
        // Color sólido
        element.setAttribute("fill", color);
        element.setAttribute("stroke", color);
      }
    });

    // Actualizar leyenda
    const legendItems = svg.querySelectorAll(`[data-legend-series="${seriesName}"]`);
    legendItems.forEach(item => {
      const colorBox = item.querySelector("rect, circle, line");
      if (colorBox) {
        if (colorBox.tagName === "line") {
          colorBox.setAttribute("stroke", color);
        } else {
          colorBox.setAttribute("fill", color);
          colorBox.setAttribute("stroke", color);
        }
      }
    });
  },

  /**
   * Oscurece un color hexadecimal
   */
  darkenColor(hex, amount) {
    const num = parseInt(hex.replace("#", ""), 16);
    const r = Math.max(0, Math.min(255, (num >> 16) - Math.round(255 * amount)));
    const g = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) - Math.round(255 * amount)));
    const b = Math.max(0, Math.min(255, (num & 0x0000FF) - Math.round(255 * amount)));
    return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
  },

  /**
   * Determina si un color es oscuro (útil para decidir color de texto)
   */
  isColorDark(hex) {
    const num = parseInt(hex.replace("#", ""), 16);
    const r = (num >> 16) & 0xFF;
    const g = (num >> 8) & 0xFF;
    const b = num & 0xFF;
    // Calcular luminosidad relativa (fórmula estándar)
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance < 0.5;
  },

  /**
   * Obtiene los colores de texto guardados para un widget
   */
  getSavedTextColors(widgetId, widgetSchema) {
    const storageKey = `widget_text_colors_${widgetId}`;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn("Error cargando colores de texto guardados:", e);
    }
    
    // Si hay colores de texto en la configuración del widget, usarlos
    return widgetSchema.text_color_mapping || {};
  },

  /**
   * Guarda los colores de texto personalizados
   */
  saveTextColors(widgetId, textColors) {
    const storageKey = `widget_text_colors_${widgetId}`;
    try {
      localStorage.setItem(storageKey, JSON.stringify(textColors));
    } catch (e) {
      console.warn("Error guardando colores de texto:", e);
    }
  },

  /**
   * Obtiene los tamaños de fuente guardados para un widget
   */
  getSavedFontSizes(widgetId, widgetSchema) {
    const storageKey = `widget_font_sizes_${widgetId}`;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn("Error cargando tamaños de fuente guardados:", e);
    }
    
    // Si hay tamaños de fuente en la configuración del widget, usarlos
    return widgetSchema.font_size_mapping || {};
  },

  /**
   * Guarda los tamaños de fuente personalizados
   */
  saveFontSizes(widgetId, fontSizes) {
    const storageKey = `widget_font_sizes_${widgetId}`;
    try {
      localStorage.setItem(storageKey, JSON.stringify(fontSizes));
    } catch (e) {
      console.warn("Error guardando tamaños de fuente:", e);
    }
  },

  /**
   * Aplica un tamaño de fuente a una serie específica del gráfico en tiempo real
   */
  applyFontSizeToChart(container, seriesName, fontSize, widgetSchema) {
    const contentElement = container.querySelector("[data-widget-content]");
    if (!contentElement) return;

    const svgElement = contentElement.querySelector("svg");
    if (!svgElement || !window.d3) return;

    // Usar D3.js para seleccionar y actualizar los textos
    const svg = d3.select(svgElement);

    // Buscar textos por atributo data-series
    svg.selectAll(`text[data-series="${seriesName}"]`)
      .attr("font-size", fontSize)
      .style("font-size", `${fontSize}px`);

    // También buscar textos que estén dentro de las barras de esta serie usando coordenadas
    const seriesRects = svg.selectAll(`rect[data-series="${seriesName}"]`);
    
    seriesRects.each(function() {
      const rect = d3.select(this);
      const barX = parseFloat(rect.attr("x") || 0);
      const barY = parseFloat(rect.attr("y") || 0);
      const barWidth = parseFloat(rect.attr("width") || 0);
      const barHeight = parseFloat(rect.attr("height") || 0);
      
      // Buscar textos que estén dentro del área de esta barra
      svg.selectAll("text").each(function() {
        const text = d3.select(this);
        const textX = parseFloat(text.attr("x") || 0);
        const textY = parseFloat(text.attr("y") || 0);
        
        // Verificar si el texto está dentro del área de la barra (con tolerancia)
        const tolerance = 10;
        if (textX >= barX - tolerance && textX <= barX + barWidth + tolerance && 
            textY >= barY - tolerance && textY <= barY + barHeight + tolerance) {
          // Solo actualizar si el texto no tiene ya un data-series diferente asignado
          const existingSeries = text.attr("data-series");
          if (!existingSeries || existingSeries === seriesName) {
            text.attr("font-size", fontSize)
                .style("font-size", `${fontSize}px`);
          }
        }
      });
    });
  },

  /**
   * Aplica un color de texto a una serie específica del gráfico en tiempo real
   */
  applyTextColorToChart(container, seriesName, textColor, widgetSchema) {
    const contentElement = container.querySelector("[data-widget-content]");
    if (!contentElement) return;

    const svgElement = contentElement.querySelector("svg");
    if (!svgElement || !window.d3) return;

    // Usar D3.js para seleccionar y actualizar los textos (más eficiente y confiable)
    const svg = d3.select(svgElement);

    // Método 1: Buscar textos por atributo data-series (más directo y eficiente)
    svg.selectAll(`text[data-series="${seriesName}"]`)
      .attr("fill", textColor)
      .style("fill", textColor);

    // Método 2: Buscar textos que estén dentro de las barras de esta serie usando coordenadas
    // Primero, obtener todas las barras (rects) de esta serie
    const seriesRects = svg.selectAll(`rect[data-series="${seriesName}"]`);
    
    seriesRects.each(function() {
      const rect = d3.select(this);
      const barX = parseFloat(rect.attr("x") || 0);
      const barY = parseFloat(rect.attr("y") || 0);
      const barWidth = parseFloat(rect.attr("width") || 0);
      const barHeight = parseFloat(rect.attr("height") || 0);
      
      // Buscar textos que estén dentro del área de esta barra
      svg.selectAll("text").each(function() {
        const text = d3.select(this);
        const textX = parseFloat(text.attr("x") || 0);
        const textY = parseFloat(text.attr("y") || 0);
        
        // Verificar si el texto está dentro del área de la barra (con tolerancia)
        const tolerance = 10; // 10px de tolerancia para capturar textos cercanos
        if (textX >= barX - tolerance && textX <= barX + barWidth + tolerance && 
            textY >= barY - tolerance && textY <= barY + barHeight + tolerance) {
          // Solo actualizar si el texto no tiene ya un data-series diferente asignado
          const existingSeries = text.attr("data-series");
          if (!existingSeries || existingSeries === seriesName) {
            text.attr("fill", textColor)
                .style("fill", textColor);
          }
        }
      });
    });
  },

  /**
   * Renderiza un widget KPI (tarjeta con valor)
   * @param {HTMLElement} container - Contenedor del widget
   * @param {Object} widgetSchema - Schema del widget
   */
  renderKPI(container, widgetSchema) {
    const metricName = widgetSchema.y_metrics?.[0];
    if (!metricName) {
      container.innerHTML = `<p class="p-4 text-sm text-slate-500">Métrica no especificada</p>`;
      return;
    }

    const metric = this.schema.metrics.find(m => m.name === metricName);
    const total = this.queryResult.totals?.[metricName] || 0;
    const formattedValue = this.formatMetric(total, metric);

    container.className = "p-6 sm:p-8";
    container.innerHTML = `
      <div class="flex flex-col items-center justify-center text-center">
        <div class="text-4xl sm:text-5xl font-bold text-slate-900 dark:text-white mb-2">
          ${formattedValue}
        </div>
        <div class="text-sm sm:text-base text-slate-600 dark:text-slate-400">
          ${metric ? metric.label : metricName}
        </div>
      </div>
    `;
  },

  /**
   * Renderiza un gráfico de barras
   * @param {HTMLElement} container - Contenedor del widget
   * @param {Object} widgetSchema - Schema del widget
   */
  renderBarChart(container, widgetSchema) {
    if (!window.d3) {
      container.innerHTML = `<p class="p-4 text-sm text-slate-500">D3.js no está disponible</p>`;
      return;
    }

    const data = this.queryResult.data || [];
    const xDimension = widgetSchema.x_dimension;
    const yMetrics = widgetSchema.y_metrics || [];
    let seriesDimension = widgetSchema.series_dimension;
    // Normalizar serie "Sucursal" -> nombre_sucursal cuando los datos tienen esa columna (reportes legacy/ventas_netas)
    if (seriesDimension && data.length > 0 && data[0].nombre_sucursal !== undefined) {
      const s = String(seriesDimension).toLowerCase();
      if (s === 'sucursal' || s === 'nombre_sucursal') {
        seriesDimension = 'nombre_sucursal';
      }
    }

    if (!xDimension || yMetrics.length === 0) {
      container.innerHTML = `<p class="p-4 text-sm text-slate-500">Dimensiones o métricas no especificadas</p>`;
      return;
    }

    container.className = "p-4 sm:p-6";
    
    // Detectar si estamos en workspace y si es ventas_netas para aplicar restricciones de altura
    const isWorkspace = this.rootElement?.closest("[data-workspace-mode]");
    const isVentasNetas = this.reportSlug === "ventas-netas";
    
    // Obtener dimensiones del contenedor - usar múltiples métodos para asegurar que tengamos dimensiones válidas
    let width = container.clientWidth || container.offsetWidth || container.getBoundingClientRect().width || 800;
    
    // Para ventas_netas en workspace, calcular altura dinámicamente para usar todo el espacio disponible
    // Similar a como "Pedidos Pendientes" utiliza todo el alto del widget
    let height;
    if (isWorkspace && isVentasNetas) {
      // Obtener la altura disponible del contenedor padre (el widget completo)
      const widgetContainer = container.closest("[data-widget-id]");
      if (widgetContainer) {
        const widgetHeight = widgetContainer.offsetHeight || widgetContainer.clientHeight || 0;
        const header = widgetContainer.querySelector("header");
        // Para ventas_netas en workspace, el header está oculto, así que no cuenta
        const headerHeight = header && !header.classList.contains("hidden") ? (header.offsetHeight || 60) : 0;
        const padding = 48; // 24px arriba + 24px abajo (p-6 = 1.5rem = 24px)
        // Para ventas_netas en workspace, las notas NO se muestran (como en Pedidos Pendientes)
        const notesHeight = 0; // Siempre 0 ya que no se muestran notas
        
        // Calcular altura disponible: altura total del widget - header - padding - notas
        const availableHeight = widgetHeight - headerHeight - padding - notesHeight;
        
        // Usar al menos 300px pero preferir usar todo el espacio disponible
        height = Math.max(300, availableHeight - 20); // -20px para márgenes internos del SVG
        console.log(`[WidgetEngine.renderBarChart] Altura calculada para ventas_netas:`, {
          widgetHeight,
          headerHeight,
          padding,
          notesHeight,
          availableHeight,
          finalHeight: height
        });
      } else {
        height = 300; // Fallback si no se puede calcular
      }
    } else {
      height = 400; // Altura estándar para otros casos
    }
    
    // Si el contenedor no tiene ancho (está oculto o no tiene dimensiones), usar un ancho por defecto
    // y forzar que el contenedor sea visible
    if (width <= 0 || !width) {
      console.warn(`[WidgetEngine.renderBarChart] Contenedor sin ancho (${width}), usando ancho por defecto y forzando visibilidad`);
      // Asegurar que el contenedor y sus padres sean visibles
      container.style.display = "block";
      container.style.visibility = "visible";
      container.style.width = "100%";
      container.style.minWidth = "400px";
      
      // Intentar obtener el ancho del contenedor padre si este no tiene
      const parent = container.parentElement;
      if (parent) {
        const parentWidth = parent.clientWidth || parent.offsetWidth || parent.getBoundingClientRect().width;
        if (parentWidth > 0) {
          width = parentWidth - 48;
        } else {
          width = 800; // Ancho por defecto
        }
      } else {
        width = 800; // Ancho por defecto
      }
    } else {
      width = width - 48; // Restar padding
    }
    
    const margin = { top: 20, right: 20, bottom: 60, left: 90 };

    // Limpiar contenido previo
    container.innerHTML = "";
    
    console.log(`[WidgetEngine.renderBarChart] Dimensiones del gráfico: width=${width}, height=${height}, containerWidth=${container.clientWidth}, containerOffsetWidth=${container.offsetWidth}`);
    
    const svg = d3.select(container)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .style("display", "block"); // Asegurar que el SVG sea visible

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Preparar datos: agregar por xDimension y seriesDimension si existe
    let processedData;
    if (seriesDimension) {
      // Agrupar por xDimension y seriesDimension, luego sumar métricas
      // IMPORTANTE: Puede haber múltiples filas con la misma combinación de xDimension y seriesDimension
      // (por ejemplo, múltiples puntos de venta de la misma sucursal en el mismo mes)
      // Por lo tanto, debemos SUMAR todas las métricas de todas las filas que coincidan
      const grouped = {};
      data.forEach(d => {
        const xKey = String(d[xDimension] || '').trim();
        const seriesKey = String(d[seriesDimension] || 'Sin serie').trim();
        const key = `${xKey}|${seriesKey}`;
        
        if (!grouped[key]) {
          grouped[key] = {
            [xDimension]: xKey,
            [seriesDimension]: seriesKey,
            _rowCount: 0  // Contador de filas para debug
          };
          yMetrics.forEach(metric => {
            grouped[key][metric] = 0;
          });
        }
        
        grouped[key]._rowCount += 1;
        
        // Sumar todas las métricas de esta fila
        yMetrics.forEach(metric => {
          const value = parseFloat(d[metric] || 0);
          if (!isNaN(value)) {
            grouped[key][metric] += value;
          }
        });
      });
      
      // Eliminar el contador de debug antes de crear processedData
      Object.values(grouped).forEach(g => delete g._rowCount);
      processedData = Object.values(grouped);
      
      // Debug: Log para verificar agrupación
      console.log('📊 Datos agrupados:', {
        totalInputRows: data.length,
        totalGroups: processedData.length,
        sampleGroups: processedData.slice(0, 10).map(g => ({
          x: g[xDimension],
          series: g[seriesDimension],
          metrics: yMetrics.reduce((acc, m) => {
            acc[m] = g[m] || 0;
            return acc;
          }, {})
        }))
      });
      
      // Verificar si hay duplicados que deberían haberse sumado
      const duplicateCheck = {};
      data.forEach(d => {
        const xKey = String(d[xDimension] || '').trim();
        const seriesKey = String(d[seriesDimension] || 'Sin serie').trim();
        const key = `${xKey}|${seriesKey}`;
        if (!duplicateCheck[key]) {
          duplicateCheck[key] = 0;
        }
        duplicateCheck[key] += 1;
      });
      const duplicates = Object.entries(duplicateCheck).filter(([k, v]) => v > 1);
      if (duplicates.length > 0) {
        console.log('📊 Combinaciones con múltiples filas (deben sumarse):', duplicates.map(([k, v]) => `${k}: ${v} filas`));
      }
    } else {
      // Agrupar solo por xDimension y sumar métricas
      const grouped = {};
      data.forEach(d => {
        const xKey = d[xDimension];
        if (!grouped[xKey]) {
          grouped[xKey] = { [xDimension]: xKey };
          yMetrics.forEach(metric => {
            grouped[xKey][metric] = 0;
          });
        }
        yMetrics.forEach(metric => {
          grouped[xKey][metric] += parseFloat(d[metric] || 0);
        });
      });
      processedData = Object.values(grouped);
    }

    const xValues = [...new Set(processedData.map(d => d[xDimension]))].sort();
    // Paleta de colores vibrantes y modernos con degradados (valores por defecto)
    const defaultColorGradients = [
      { start: "#8b5cf6", end: "#a78bfa" }, // Púrpura vibrante
      { start: "#06b6d4", end: "#22d3ee" }, // Cyan brillante
      { start: "#f59e0b", end: "#fbbf24" }, // Naranja dorado
      { start: "#10b981", end: "#34d399" }, // Verde esmeralda
      { start: "#ef4444", end: "#f87171" }, // Rojo coral
      { start: "#3b82f6", end: "#60a5fa" }, // Azul cielo
    ];
    // Colores sólidos para gráficos no apilados (valores por defecto)
    const defaultColors = ["#8b5cf6", "#06b6d4", "#f59e0b", "#10b981", "#ef4444", "#3b82f6"];

    // Permitir colores personalizados desde la configuración del widget o localStorage
    // Formato esperado en widgetSchema:
    //   color_mapping: { "Casa Matríz": "#06b6d4", "Sucursal 2": "#10b981", ... }
    //   color_gradients: { "Casa Matríz": { start: "#06b6d4", end: "#22d3ee" }, ... }
    //   text_color_mapping: { "Casa Matríz": "#ffffff", "Sucursal 2": "#1e293b", ... }
    const widgetId = container.closest("[data-widget-id]")?.getAttribute("data-widget-id");
    const savedColors = widgetId ? this.getSavedColors(widgetId, widgetSchema) : {};
    const savedTextColors = widgetId ? this.getSavedTextColors(widgetId, widgetSchema) : {};
    const savedFontSizes = widgetId ? this.getSavedFontSizes(widgetId, widgetSchema) : {};
    const colorMapping = { ...(widgetSchema.color_mapping || {}), ...savedColors };
    const textColorMapping = { ...(widgetSchema.text_color_mapping || {}), ...savedTextColors };
    const fontSizeMapping = { ...(widgetSchema.font_size_mapping || {}), ...savedFontSizes };
    const gradientMapping = widgetSchema.color_gradients || {};
    
    // Construir arrays de colores/gradientes respetando el orden de las series
    let colorGradients = [];
    let colors = [];
    
    if (seriesDimension) {
      const seriesValues = [...new Set(processedData.map(d => d[seriesDimension]))].sort();
      seriesValues.forEach((series, index) => {
        // Si hay un color personalizado guardado o en configuración, usarlo
        const customColor = colorMapping[series];
        
        if (customColor) {
          // Crear gradiente basado en el color personalizado
          const darkerColor = this.darkenColor(customColor, 0.2);
          colorGradients.push({ start: customColor, end: darkerColor });
          colors.push(customColor);
        } else if (gradientMapping[series]) {
          // Si hay un gradiente personalizado para esta serie, usarlo
          colorGradients.push(gradientMapping[series]);
          colors.push(gradientMapping[series].start);
        } else {
          // Usar gradiente por defecto
          colorGradients.push(defaultColorGradients[index % defaultColorGradients.length]);
          colors.push(defaultColors[index % defaultColors.length]);
        }
      });
    } else {
      // Si no hay series, usar los arrays por defecto
      colorGradients = [...defaultColorGradients];
      colors = [...defaultColors];
    }

    // Calcular el ancho necesario para la leyenda si hay series
    let legendWidth = 0;
    if (seriesDimension) {
      const tempSeriesValues = [...new Set(data.map(d => String(d[seriesDimension] || 'Sin serie').trim()))].sort();
      const maxSeriesLength = Math.max(...tempSeriesValues.map(s => s.length), 0);
      // Ancho del cuadrado (12px) + espacio (6px) + ancho del texto (aproximadamente 6.5px por carácter) + margen (20px)
      legendWidth = 12 + 6 + (maxSeriesLength * 6.5) + 20;
      legendWidth = Math.max(legendWidth, 150); // Mínimo 150px
    }
    
    // Reducir el ancho disponible para las barras para dejar espacio para la leyenda
    // Esto solo afecta el área donde se dibujan las barras, no todo el gráfico
    const barAreaWidth = chartWidth - legendWidth;

    // Escalas
    const xScale = d3.scaleBand()
      .domain(xValues)
      .range([0, barAreaWidth])
      .padding(0.2);

    // Calcular máximo valor con datos procesados
    const maxValue = d3.max(processedData, d => {
      return yMetrics.reduce((sum, metric) => sum + (parseFloat(d[metric]) || 0), 0);
    });

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([chartHeight, 0]);

    // Detectar modo oscuro
    const isDarkMode = document.documentElement.classList.contains('dark') || 
                      window.matchMedia('(prefers-color-scheme: dark)').matches;
    const axisTextColor = isDarkMode ? "#e2e8f0" : "#64748b"; // slate-200 en oscuro, slate-500 en claro
    const axisLineColor = isDarkMode ? "#475569" : "#cbd5e1"; // slate-600 en oscuro, slate-300 en claro
    
    // Ejes
    const xAxis = g.append("g")
      .attr("transform", `translate(0,${chartHeight})`)
      .call(d3.axisBottom(xScale));
    
    // Estilizar etiquetas del eje X
    xAxis.selectAll("text")
      .style("text-anchor", "middle")
      .attr("dx", "0")
      .attr("dy", ".35em")
      .style("fill", axisTextColor)
      .style("font-size", "11px");
    
    // Estilizar líneas y ticks del eje X
    xAxis.selectAll("line")
      .style("stroke", axisLineColor);
    xAxis.selectAll("path")
      .style("stroke", axisLineColor);

    // Usar isVentasNetas ya declarada arriba (línea 974) para aplicar formateo en millones
    const yAxis = g.append("g")
      .call(d3.axisLeft(yScale).tickFormat(d => {
        // Para ventas-netas, mostrar valores en millones con 2 decimales
        return isVentasNetas ? this.formatMillions(d) : this.formatNumber(d, 0);
      }));
    
    // Estilizar etiquetas del eje Y
    yAxis.selectAll("text")
      .style("text-anchor", "end")
      .attr("dx", "-0.5em")
      .style("fill", axisTextColor)
      .style("font-size", "11px");
    
    // Estilizar líneas y ticks del eje Y
    yAxis.selectAll("line")
      .style("stroke", axisLineColor);
    yAxis.selectAll("path")
      .style("stroke", axisLineColor);

    // Barras
    if (seriesDimension && widgetSchema.options?.stacked) {
      // Gráfico apilado por serie (seriesDimension)
      const seriesValues = [...new Set(processedData.map(d => d[seriesDimension]))].sort();
      
      // Debug: Log para verificar datos procesados
      console.log('📊 Datos procesados para gráfico apilado:', {
        totalRows: processedData.length,
        xValues: xValues,
        seriesValues: seriesValues,
        sampleData: processedData.slice(0, 5)
      });
      
      // Crear datos apilados: para cada xValue, sumar valores por serie
      // IMPORTANTE: processedData ya está agrupado por xDimension y seriesDimension,
      // así que cada combinación debería tener solo una fila
      const seriesData = xValues.map(xVal => {
        const result = { [xDimension]: xVal };
        seriesValues.forEach(series => {
          // Buscar la fila que corresponde a esta combinación de xVal y series
          const row = processedData.find(d => 
            String(d[xDimension] || '').trim() === String(xVal).trim() && 
            String(d[seriesDimension] || '').trim() === String(series).trim()
          );
          
          // Si no se encuentra, buscar todas las filas que coincidan (por si hay duplicados)
          const rows = processedData.filter(d => 
            String(d[xDimension] || '').trim() === String(xVal).trim() && 
            String(d[seriesDimension] || '').trim() === String(series).trim()
          );
          
          // Sumar todas las métricas de todas las filas encontradas
          const total = rows.reduce((sum, row) => {
            return sum + yMetrics.reduce((metricSum, metric) => {
              const value = parseFloat(row[metric] || 0);
              return metricSum + (isNaN(value) ? 0 : value);
            }, 0);
          }, 0);
          
          result[series] = total;
          
          // Debug: Log para verificar sumas
          if (rows.length > 0) {
            const metricValues = rows.map(r => 
              yMetrics.map(m => parseFloat(r[m] || 0)).reduce((a, b) => a + b, 0)
            );
            console.log(`📊 ${xVal} | ${series}: ${rows.length} fila(s), valores individuales: [${metricValues.map(v => v.toLocaleString('es-AR', {style: 'currency', currency: 'ARS'})).join(', ')}], total = ${total.toLocaleString('es-AR', {style: 'currency', currency: 'ARS'})}`);
          } else {
            console.warn(`⚠️ ${xVal} | ${series}: No se encontraron filas`);
          }
        });
        return result;
      });
      
      // Debug: Log de datos finales para el stack
      console.log('📊 Datos finales para stack:', seriesData);

      // Crear stack usando las series como claves
      const stack = d3.stack()
        .keys(seriesValues)
        .order(d3.stackOrderNone)
        .offset(d3.stackOffsetNone);

      const stackedData = stack(seriesData);

      // Crear degradados SVG para cada serie
      const defs = svg.append("defs");
      colorGradients.forEach((gradient, index) => {
        const grad = defs.append("linearGradient")
          .attr("id", `gradient-${index}`)
          .attr("x1", "0%")
          .attr("y1", "0%")
          .attr("x2", "0%")
          .attr("y2", "100%");
        
        grad.append("stop")
          .attr("offset", "0%")
          .attr("stop-color", gradient.start)
          .attr("stop-opacity", 1);
        
        grad.append("stop")
          .attr("offset", "100%")
          .attr("stop-color", gradient.end)
          .attr("stop-opacity", 1);
      });

      // Crear tooltip para mostrar valores detallados al hacer hover
      const tooltip = d3.select("body")
        .append("div")
        .attr("class", "absolute bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-2xl pointer-events-none opacity-0 z-50 border border-slate-700")
        .style("font-family", "system-ui, sans-serif")
        .style("min-width", "150px")
        .style("max-width", "250px")
        .style("transition", "opacity 0.2s ease-in-out");

      const groups = g.selectAll(".series")
        .data(stackedData)
        .enter()
        .append("g")
        .attr("class", "series")
        .attr("data-series", d => d.key);

      // Calcular el total del stack para cada xValue (para usar en tooltips)
      // El total es el d[1] del último layer para cada xValue
      const stackTotals = new Map();
      if (stackedData.length > 0) {
        const topLayer = stackedData[stackedData.length - 1];
        topLayer.forEach(d => {
          const xValue = d.data[xDimension];
          // d[1] del último layer es el total acumulado del stack completo
          stackTotals.set(xValue, d[1]);
        });
      }

      // Obtener el schema de métrica para el total (para usar en tooltips)
      const totalMetricSchema = yMetrics.length > 0
        ? this.schema.metrics.find(m => m.name === yMetrics[0]) || { data_type: "currency" }
        : { data_type: "currency" };

      // Crear rectángulos con tooltips interactivos y degradados
      // Capturar el contexto de WidgetEngine para usar en los callbacks
      const widgetEngine = this;
      
      stackedData.forEach((layer, layerIndex) => {
        const seriesName = layer.key;
        const gradientId = `gradient-${layerIndex % colorGradients.length}`;
        const metricSchema = yMetrics.length > 0 
          ? this.schema.metrics.find(m => m.name === yMetrics[0]) 
          : { data_type: "currency" };

        groups.filter((d, i) => i === layerIndex)
          .selectAll("rect")
          .data(layer)
          .enter()
          .append("rect")
          .attr("x", d => xScale(d.data[xDimension]))
          .attr("y", d => yScale(d[1]))
          .attr("height", d => yScale(d[0]) - yScale(d[1]))
          .attr("width", xScale.bandwidth())
          .attr("fill", `url(#${gradientId})`)
          .attr("data-series", seriesName)
          .attr("opacity", 0.95)
          .style("cursor", "pointer")
          .on("mouseover", function(event, d) {
            const segmentHeight = yScale(d[0]) - yScale(d[1]);
            const value = d[1] - d[0];
            // Obtener el total del stack para este xValue
            const totalValue = stackTotals.get(d.data[xDimension]) || 0;
            const percentage = totalValue > 0 ? ((value / totalValue) * 100).toFixed(1) : "0";
            
            // Obtener el nombre de la métrica
            const metricName = yMetrics.length > 0 
              ? (widgetEngine.schema.metrics.find(m => m.name === yMetrics[0])?.label || yMetrics[0])
              : "Valor";
            
            d3.select(this).attr("opacity", 1).attr("stroke", "#ffffff").attr("stroke-width", 2);
            
            // Para ventas-netas, mostrar valores en millones con 2 decimales (solo visual)
            const isVentasNetas = widgetEngine.reportSlug === "ventas-netas";
            const formattedValue = isVentasNetas ? widgetEngine.formatMillions(value) : widgetEngine.formatMetric(value, metricSchema);
            const formattedTotal = isVentasNetas ? widgetEngine.formatMillions(totalValue) : widgetEngine.formatMetric(totalValue, totalMetricSchema);
            
            tooltip
              .html(`
                <div class="mb-2">
                  <div class="font-bold text-sm text-white mb-0.5">${seriesName}</div>
                  <div class="text-sky-300 text-[10px] font-medium">${xDimension}: ${d.data[xDimension]}</div>
                </div>
                <div class="py-2 border-t border-slate-700">
                  <div class="text-slate-400 text-[9px] uppercase tracking-wide mb-1">${metricName}</div>
                  <div class="text-emerald-300 font-bold text-base mb-1">${formattedValue}</div>
                  <div class="flex items-center justify-between gap-3 mt-2 pt-2 border-t border-slate-700">
                    <div class="text-slate-400 text-[9px]">Porcentaje:</div>
                    <div class="text-white font-semibold text-xs">${percentage}%</div>
                  </div>
                  <div class="flex items-center justify-between gap-3 mt-1">
                    <div class="text-slate-400 text-[9px]">Total del mes:</div>
                    <div class="text-sky-300 font-semibold text-xs">${formattedTotal}</div>
                  </div>
                </div>
              `)
              .style("opacity", 1);
          })
          .on("mousemove", function(event) {
            tooltip
              .style("left", (event.pageX + 10) + "px")
              .style("top", (event.pageY - 10) + "px");
          })
          .on("mouseout", function() {
            d3.select(this).attr("opacity", 0.95).attr("stroke", "none");
            tooltip.style("opacity", 0);
          });
      });

      // Agregar etiquetas de valor en el gráfico apilado
      // Opción 7: Combinación híbrida
      // - Mostrar etiquetas solo en segmentos >30px
      // - Ocultar etiquetas en segmentos <30px
      // - No mostrar etiquetas en el último segmento (donde va el total) para evitar superposiciones
      // - Tooltip al hover para mostrar todos los valores
      stackedData.forEach((layer, layerIndex) => {
        const seriesName = layer.key;
        const metricSchema = yMetrics.length > 0 
          ? this.schema.metrics.find(m => m.name === yMetrics[0]) 
          : { data_type: "currency" };
        
        const isLastLayer = layerIndex === stackedData.length - 1;
        
        // Obtener el índice de la serie en seriesValues para acceder al color correcto
        const seriesIndexInArray = seriesValues.indexOf(seriesName);
        const seriesColor = seriesIndexInArray >= 0 ? colors[seriesIndexInArray % colors.length] : colors[layerIndex % colors.length];
        const textColor = textColorMapping[seriesName] || (this.isColorDark(seriesColor) ? "#ffffff" : "#1e293b");
        const fontSize = fontSizeMapping[seriesName] || 9;
        
        // Agregar etiquetas de texto solo en segmentos suficientemente altos
        g.selectAll(`.stack-label-${layerIndex}`)
          .data(layer)
          .enter()
          .append("text")
          .attr("class", `stack-label-${layerIndex}`)
          .attr("data-series", seriesName)
          .attr("x", d => xScale(d.data[xDimension]) + xScale.bandwidth() / 2)
          .attr("y", d => {
            const segmentHeight = yScale(d[0]) - yScale(d[1]);
            
            // Umbral aumentado a 30px para evitar superposiciones
            if (segmentHeight < 30) return -999; // Fuera de la vista
            
            // Si es el último segmento (el superior), no mostrar etiqueta individual
            // porque el total ya se muestra arriba
            if (isLastLayer) return -999;
            
            // Calcular la posición del centro del segmento
            return yScale(d[1]) + segmentHeight / 2;
          })
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "middle")
          .style("font-size", `${fontSize}px`)
          .style("fill", textColor)
          .style("font-weight", "600")
          .style("text-shadow", "0 1px 2px rgba(0,0,0,0.3)")
          .style("pointer-events", "none")
          .text(d => {
            const value = d[1] - d[0];
            if (value === 0 || value < 0) return "";
            // Para ventas-netas, mostrar valores en millones con 2 decimales (solo visual)
            const isVentasNetas = this.reportSlug === "ventas-netas";
            return isVentasNetas ? this.formatMillions(value) : this.formatMetric(value, metricSchema || { data_type: "currency" });
          });
      });
      
      // Agregar etiqueta del total en la parte superior de cada stack (última capa)
      // Esta etiqueta SIEMPRE se muestra, independientemente del tamaño de los segmentos
      // En D3 stack: d[0] = base del segmento, d[1] = top del segmento
      // Para el último layer, d[1] es el total acumulado del stack completo
      if (stackedData.length > 0) {
        const topLayer = stackedData[stackedData.length - 1];
        const totalMetricSchema = yMetrics.length > 0
          ? this.schema.metrics.find(m => m.name === yMetrics[0]) || { data_type: "currency" }
          : { data_type: "currency" };
        
        // Detectar modo oscuro
        const isDarkMode = document.documentElement.classList.contains('dark') || 
                          window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        g.selectAll(".stack-total-label")
          .data(topLayer)
          .enter()
          .append("text")
          .attr("class", "stack-total-label")
          .attr("x", d => xScale(d.data[xDimension]) + xScale.bandwidth() / 2)
          .attr("y", d => {
            // d[1] es el valor superior del último segmento = total acumulado del stack
            // Posicionar en la parte superior del stack con suficiente espacio
            // Aumentar el espacio a 20px para evitar superposiciones
            return yScale(d[1]) - 20;
          })
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "middle")
          .style("font-size", "11px")
          .style("fill", isDarkMode ? "#ffffff" : "#1e293b")
          .style("font-weight", "700")
          .style("text-shadow", isDarkMode ? "0 1px 3px rgba(0,0,0,0.8)" : "0 1px 3px rgba(255,255,255,0.8)")
          .style("pointer-events", "none")
          .text(d => {
            // d[1] del último layer es el valor total acumulado del stack completo
            const totalValue = d[1];
            if (totalValue === 0 || totalValue < 0) return "";
            // Para ventas-netas, mostrar valores en millones con 2 decimales (solo visual)
            const isVentasNetas = this.reportSlug === "ventas-netas";
            return isVentasNetas ? this.formatMillions(totalValue) : this.formatMetric(totalValue, totalMetricSchema);
          });
      }
      
      // Limpiar tooltip al salir del área del gráfico
      svg.on("mouseleave", () => {
        tooltip.style("opacity", 0);
        // Restaurar opacidad de todos los rectángulos
        groups.selectAll("rect").attr("opacity", 0.95);
      });
      
      // Agregar leyenda para las series
      // Posicionar la leyenda a la derecha del área de barras
      const legendX = barAreaWidth + 20; // Después del área de barras + margen
      const legend = g.append("g")
        .attr("transform", `translate(${legendX}, 10)`);

      // Detectar modo oscuro para la leyenda
      const isDarkModeLegend = document.documentElement.classList.contains('dark') || 
                               window.matchMedia('(prefers-color-scheme: dark)').matches;
      const legendTextColor = isDarkModeLegend ? "#e2e8f0" : "#64748b"; // slate-200 en oscuro, slate-500 en claro

      seriesValues.forEach((series, seriesIndex) => {
        const legendItem = legend.append("g")
          .attr("transform", `translate(0, ${seriesIndex * 20})`)
          .attr("data-legend-series", series);

        legendItem.append("rect")
          .attr("x", 0)
          .attr("y", -6)
          .attr("width", 12)
          .attr("height", 12)
          .attr("fill", colors[seriesIndex % colors.length]);

        legendItem.append("text")
          .attr("x", 18)
          .attr("y", 4)
          .style("font-size", "11px")
          .style("fill", legendTextColor)
          .text(series);
      });
    } else if (seriesDimension) {
      // Gráfico agrupado (múltiples barras por xValue, una por serie)
      const seriesValues = [...new Set(processedData.map(d => d[seriesDimension]))].sort();
      const barWidth = xScale.bandwidth() / seriesValues.length;

      seriesValues.forEach((series, seriesIndex) => {
        const seriesData = xValues.map(xVal => {
          const row = processedData.find(d => d[xDimension] === xVal && d[seriesDimension] === series);
          // Si yMetrics está vacío, intentar usar la primera métrica disponible o sumar todas
          let value = 0;
          if (yMetrics.length > 0) {
            value = parseFloat(row?.[yMetrics[0]] || 0);
          } else {
            // Si no hay yMetrics, sumar todas las métricas numéricas disponibles
            if (row) {
              Object.keys(row).forEach(key => {
                if (key !== xDimension && key !== seriesDimension && !isNaN(parseFloat(row[key]))) {
                  value += parseFloat(row[key] || 0);
                }
              });
            }
          }
          return {
            x: xVal,
            y: value,
            value: value
          };
        });

        const bars = g.selectAll(`.bar-${seriesIndex}`)
          .data(seriesData)
          .enter()
          .append("rect")
          .attr("class", `bar-${seriesIndex}`)
          .attr("x", d => xScale(d.x) + barWidth * seriesIndex)
          .attr("y", d => yScale(d.y))
          .attr("width", barWidth * 0.9)
          .attr("height", d => chartHeight - yScale(d.y))
          .attr("fill", colors[seriesIndex % colors.length]);

        // Agregar etiquetas de valor sobre las barras
        const metric = this.schema.metrics.find(m => m.name === yMetrics[0]);
        g.selectAll(`.label-${seriesIndex}`)
          .data(seriesData)
          .enter()
          .append("text")
          .attr("class", `label-${seriesIndex}`)
          .attr("x", d => xScale(d.x) + barWidth * seriesIndex + barWidth * 0.45)
          .attr("y", d => {
            const barHeight = chartHeight - yScale(d.y);
            // Si la barra es muy pequeña, mostrar la etiqueta arriba, si no, dentro
            return barHeight < 20 ? yScale(d.y) - 5 : yScale(d.y) + barHeight / 2;
          })
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "middle")
          .style("font-size", "10px")
          .style("fill", "#1e293b")
          .style("font-weight", "500")
          .text(d => {
            if (d.value === 0) return "";
            return this.formatMetric(d.value, metric || { data_type: "currency" });
          });
      });

      // Leyenda
      // Posicionar la leyenda a la derecha del área de barras
      const legendX = barAreaWidth + 20; // Después del área de barras + margen
      const legend = g.append("g")
        .attr("transform", `translate(${legendX}, 10)`);

      // Detectar modo oscuro para la leyenda
      const isDarkModeLegend = document.documentElement.classList.contains('dark') || 
                               window.matchMedia('(prefers-color-scheme: dark)').matches;
      const legendTextColor = isDarkModeLegend ? "#e2e8f0" : "#64748b"; // slate-200 en oscuro, slate-500 en claro

      seriesValues.forEach((series, seriesIndex) => {
        const legendItem = legend.append("g")
          .attr("transform", `translate(0, ${seriesIndex * 20})`)
          .attr("data-legend-series", series);

        legendItem.append("rect")
          .attr("x", 0)
          .attr("y", -6)
          .attr("width", 12)
          .attr("height", 12)
          .attr("fill", colors[seriesIndex % colors.length]);

        legendItem.append("text")
          .attr("x", 18)
          .attr("y", 4)
          .style("font-size", "11px")
          .style("fill", legendTextColor)
          .text(series);
      });
    } else {
      // Gráfico simple (una barra por xValue)
      yMetrics.forEach((metric, metricIndex) => {
        const metricSchema = this.schema.metrics.find(m => m.name === metric);
        const metricData = xValues.map(xVal => {
          const row = processedData.find(d => d[xDimension] === xVal);
          return {
            x: xVal,
            y: parseFloat(row?.[metric] || 0),
            value: parseFloat(row?.[metric] || 0)
          };
        });

        g.selectAll(`.bar-${metricIndex}`)
          .data(metricData)
          .enter()
          .append("rect")
          .attr("class", `bar-${metricIndex}`)
          .attr("x", d => xScale(d.x) + (xScale.bandwidth() / yMetrics.length) * metricIndex)
          .attr("y", d => yScale(d.y))
          .attr("width", xScale.bandwidth() / yMetrics.length)
          .attr("height", d => chartHeight - yScale(d.y))
          .attr("fill", colors[metricIndex % colors.length]);

        // Agregar etiquetas de valor sobre las barras
        g.selectAll(`.label-${metricIndex}`)
          .data(metricData)
          .enter()
          .append("text")
          .attr("class", `label-${metricIndex}`)
          .attr("x", d => xScale(d.x) + (xScale.bandwidth() / yMetrics.length) * metricIndex + (xScale.bandwidth() / yMetrics.length) / 2)
          .attr("y", d => {
            const barHeight = chartHeight - yScale(d.y);
            // Si la barra es muy pequeña, mostrar la etiqueta arriba, si no, dentro
            return barHeight < 20 ? yScale(d.y) - 5 : yScale(d.y) + barHeight / 2;
          })
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "middle")
          .style("font-size", "10px")
          .style("fill", "#1e293b")
          .style("font-weight", "500")
          .text(d => {
            if (d.value === 0) return "";
            return this.formatMetric(d.value, metricSchema || { data_type: "currency" });
          });
      });
    }
  },

  /**
   * Renderiza un gráfico de líneas
   * @param {HTMLElement} container - Contenedor del widget
   * @param {Object} widgetSchema - Schema del widget
   */
  renderLineChart(container, widgetSchema) {
    if (!window.d3) {
      container.innerHTML = `<p class="p-4 text-sm text-slate-500">D3.js no está disponible</p>`;
      return;
    }

    const data = this.queryResult.data || [];
    const xDimension = widgetSchema.x_dimension;
    const yMetrics = widgetSchema.y_metrics || [];
    const seriesDimension = widgetSchema.series_dimension;

    if (!xDimension || yMetrics.length === 0) {
      container.innerHTML = `<p class="p-4 text-sm text-slate-500">Dimensiones o métricas no especificadas</p>`;
      return;
    }

    container.className = "p-4 sm:p-6";
    
    // Detectar si estamos en workspace y si es ventas_netas para aplicar restricciones de altura
    const isWorkspace = this.rootElement?.closest("[data-workspace-mode]");
    const isVentasNetas = this.reportSlug === "ventas-netas";
    
    // Obtener dimensiones del contenedor - usar múltiples métodos para asegurar que tengamos dimensiones válidas
    let width = container.clientWidth || container.offsetWidth || container.getBoundingClientRect().width || 800;
    
    // Para ventas_netas en workspace, calcular altura dinámicamente para usar todo el espacio disponible
    // Similar a como "Pedidos Pendientes" utiliza todo el alto del widget
    let height;
    if (isWorkspace && isVentasNetas) {
      // Obtener la altura disponible del contenedor padre (el widget completo)
      const widgetContainer = container.closest("[data-widget-id]");
      if (widgetContainer) {
        const widgetHeight = widgetContainer.offsetHeight || widgetContainer.clientHeight || 0;
        const header = widgetContainer.querySelector("header");
        // Para ventas_netas en workspace, el header está oculto, así que no cuenta
        const headerHeight = header && !header.classList.contains("hidden") ? (header.offsetHeight || 60) : 0;
        const padding = 48; // 24px arriba + 24px abajo (p-6 = 1.5rem = 24px)
        // Para ventas_netas en workspace, las notas NO se muestran (como en Pedidos Pendientes)
        const notesHeight = 0; // Siempre 0 ya que no se muestran notas
        
        // Calcular altura disponible: altura total del widget - header - padding - notas
        const availableHeight = widgetHeight - headerHeight - padding - notesHeight;
        
        // Usar al menos 300px pero preferir usar todo el espacio disponible
        height = Math.max(300, availableHeight - 20); // -20px para márgenes internos del SVG
        console.log(`[WidgetEngine.renderLineChart] Altura calculada para ventas_netas:`, {
          widgetHeight,
          headerHeight,
          padding,
          notesHeight,
          availableHeight,
          finalHeight: height
        });
      } else {
        height = 300; // Fallback si no se puede calcular
      }
    } else {
      height = 400; // Altura estándar para otros casos
    }
    
    // Si el contenedor no tiene ancho, usar ancho por defecto y forzar visibilidad
    if (width <= 0 || !width) {
      container.style.display = "block";
      container.style.visibility = "visible";
      container.style.width = "100%";
      container.style.minWidth = "400px";
      const parent = container.parentElement;
      if (parent) {
        const parentWidth = parent.clientWidth || parent.offsetWidth || parent.getBoundingClientRect().width;
        width = parentWidth > 0 ? parentWidth - 48 : 800;
      } else {
        width = 800;
      }
    } else {
      width = width - 48;
    }
    
    const margin = { top: 20, right: 20, bottom: 60, left: 90 };

    // Limpiar contenido previo
    container.innerHTML = "";
    
    const svg = d3.select(container)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .style("display", "block"); // Asegurar que el SVG sea visible

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Preparar datos: agregar por xDimension si hay seriesDimension
    let processedData;
    if (seriesDimension) {
      // Agrupar por xDimension y seriesDimension, luego sumar métricas
      const grouped = {};
      data.forEach(d => {
        const xKey = d[xDimension];
        const seriesKey = d[seriesDimension] || 'Sin serie';
        const key = `${xKey}|${seriesKey}`;
        if (!grouped[key]) {
          grouped[key] = {
            [xDimension]: xKey,
            [seriesDimension]: seriesKey
          };
          yMetrics.forEach(metric => {
            grouped[key][metric] = 0;
          });
        }
        yMetrics.forEach(metric => {
          grouped[key][metric] += parseFloat(d[metric] || 0);
        });
      });
      processedData = Object.values(grouped);
    } else {
      // Agrupar solo por xDimension y sumar métricas
      const grouped = {};
      data.forEach(d => {
        const xKey = d[xDimension];
        if (!grouped[xKey]) {
          grouped[xKey] = { [xDimension]: xKey };
          yMetrics.forEach(metric => {
            grouped[xKey][metric] = 0;
          });
        }
        yMetrics.forEach(metric => {
          grouped[xKey][metric] += parseFloat(d[metric] || 0);
        });
      });
      processedData = Object.values(grouped);
    }

    // Ordenar por xDimension
    processedData.sort((a, b) => {
      const aVal = a[xDimension];
      const bVal = b[xDimension];
      if (aVal < bVal) return -1;
      if (aVal > bVal) return 1;
      return 0;
    });

    const xValues = [...new Set(processedData.map(d => d[xDimension]))].sort();
    const colors = ["#38bdf8", "#818cf8", "#f97316", "#10b981", "#f472b6", "#facc15"];

    // Escalas
    const xScale = d3.scalePoint()
      .domain(xValues)
      .range([0, chartWidth])
      .padding(0.5);

    // Calcular máximo valor considerando todas las métricas y series
    let maxValue = 0;
    if (seriesDimension) {
      const seriesValues = [...new Set(processedData.map(d => d[seriesDimension]))];
      seriesValues.forEach(series => {
        const seriesData = processedData.filter(d => d[seriesDimension] === series);
        yMetrics.forEach(metric => {
          const metricMax = d3.max(seriesData, d => parseFloat(d[metric] || 0));
          maxValue = Math.max(maxValue, metricMax);
        });
      });
    } else {
      yMetrics.forEach(metric => {
        const metricMax = d3.max(processedData, d => parseFloat(d[metric] || 0));
        maxValue = Math.max(maxValue, metricMax);
      });
    }

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([chartHeight, 0]);

    // Detectar modo oscuro
    const isDarkMode = document.documentElement.classList.contains('dark') || 
                      window.matchMedia('(prefers-color-scheme: dark)').matches;
    const axisTextColor = isDarkMode ? "#e2e8f0" : "#64748b"; // slate-200 en oscuro, slate-500 en claro
    const axisLineColor = isDarkMode ? "#475569" : "#cbd5e1"; // slate-600 en oscuro, slate-300 en claro
    
    // Ejes
    const xAxis = g.append("g")
      .attr("transform", `translate(0,${chartHeight})`)
      .call(d3.axisBottom(xScale));
    
    // Estilizar etiquetas del eje X
    xAxis.selectAll("text")
      .style("text-anchor", "middle")
      .attr("dx", "0")
      .attr("dy", ".35em")
      .style("fill", axisTextColor)
      .style("font-size", "11px");
    
    // Estilizar líneas y ticks del eje X
    xAxis.selectAll("line")
      .style("stroke", axisLineColor);
    xAxis.selectAll("path")
      .style("stroke", axisLineColor);

    // Usar isVentasNetas ya declarada arriba (línea 1777) para aplicar formateo en millones
    const yAxis = g.append("g")
      .call(d3.axisLeft(yScale).tickFormat(d => {
        // Para ventas-netas, mostrar valores en millones con 2 decimales
        return isVentasNetas ? this.formatMillions(d) : this.formatNumber(d, 0);
      }));
    
    // Estilizar etiquetas del eje Y
    yAxis.selectAll("text")
      .style("text-anchor", "end")
      .attr("dx", "-0.5em")
      .style("fill", axisTextColor)
      .style("font-size", "11px");
    
    // Estilizar líneas y ticks del eje Y
    yAxis.selectAll("line")
      .style("stroke", axisLineColor);
    yAxis.selectAll("path")
      .style("stroke", axisLineColor);

    // Líneas
    if (seriesDimension) {
      // Múltiples líneas (una por serie)
      const seriesValues = [...new Set(processedData.map(d => d[seriesDimension]))];
      const line = d3.line()
        .x(d => xScale(d[xDimension]))
        .y(d => yScale(d[yMetrics[0]]))
        .curve(d3.curveMonotoneX);

      seriesValues.forEach((series, seriesIndex) => {
        const seriesData = processedData
          .filter(d => d[seriesDimension] === series)
          .sort((a, b) => {
            const aVal = a[xDimension];
            const bVal = b[xDimension];
            if (aVal < bVal) return -1;
            if (aVal > bVal) return 1;
            return 0;
          });

        // Asegurar que todos los xValues tengan datos
        const completeSeriesData = xValues.map(xVal => {
          const existing = seriesData.find(d => d[xDimension] === xVal);
          if (existing) return existing;
          return {
            [xDimension]: xVal,
            [seriesDimension]: series,
            [yMetrics[0]]: 0
          };
        });

        g.append("path")
          .datum(completeSeriesData)
          .attr("fill", "none")
          .attr("stroke", colors[seriesIndex % colors.length])
          .attr("stroke-width", 2)
          .attr("data-series", series)
          .attr("d", line);

        // Puntos en la línea
        g.selectAll(`.dot-${seriesIndex}`)
          .data(completeSeriesData)
          .enter()
          .append("circle")
          .attr("class", `dot-${seriesIndex}`)
          .attr("cx", d => xScale(d[xDimension]))
          .attr("cy", d => yScale(d[yMetrics[0]]))
          .attr("r", 4)
          .attr("fill", colors[seriesIndex % colors.length])
          .attr("data-series", series);
      });

      // Leyenda
      const legend = g.append("g")
        .attr("transform", `translate(${chartWidth - 100}, 10)`);

      // Detectar modo oscuro para la leyenda
      const isDarkModeLegend = document.documentElement.classList.contains('dark') || 
                               window.matchMedia('(prefers-color-scheme: dark)').matches;
      const legendTextColor = isDarkModeLegend ? "#e2e8f0" : "#64748b"; // slate-200 en oscuro, slate-500 en claro

      seriesValues.forEach((series, seriesIndex) => {
        const legendItem = legend.append("g")
          .attr("transform", `translate(0, ${seriesIndex * 20})`)
          .attr("data-legend-series", series);

        legendItem.append("line")
          .attr("x1", 0)
          .attr("x2", 20)
          .attr("y1", 0)
          .attr("y2", 0)
          .attr("stroke", colors[seriesIndex % colors.length])
          .attr("stroke-width", 2);

        legendItem.append("text")
          .attr("x", 25)
          .attr("y", 4)
          .style("font-size", "11px")
          .style("fill", legendTextColor)
          .text(series);
      });
    } else {
      // Línea simple
      const line = d3.line()
        .x(d => xScale(d[xDimension]))
        .y(d => yScale(d[yMetrics[0]]))
        .curve(d3.curveMonotoneX);

      const lineData = processedData.sort((a, b) => {
        const aVal = a[xDimension];
        const bVal = b[xDimension];
        if (aVal < bVal) return -1;
        if (aVal > bVal) return 1;
        return 0;
      });

      g.append("path")
        .datum(lineData)
        .attr("fill", "none")
        .attr("stroke", colors[0])
        .attr("stroke-width", 2)
        .attr("d", line);

      // Puntos en la línea
      g.selectAll(".dot")
        .data(lineData)
        .enter()
        .append("circle")
        .attr("class", "dot")
        .attr("cx", d => xScale(d[xDimension]))
        .attr("cy", d => yScale(d[yMetrics[0]]))
        .attr("r", 4)
        .attr("fill", colors[0]);
    }
  },

  /**
   * Calcula una agregación sobre una columna de datos
   * @param {Array} data - Array de objetos con los datos
   * @param {string} columnName - Nombre de la columna
   * @param {string} aggregation - Tipo de agregación (sum, avg, max, min, count, count_distinct)
   * @returns {number|null} Valor agregado o null si no hay datos válidos
   */
  calculateColumnAggregation(data, columnName, aggregation) {
    if (!data || data.length === 0) return null;
    
    const values = data
      .map(row => {
        const val = row[columnName];
        if (val === null || val === undefined) return null;
        return parseFloat(val);
      })
      .filter(val => val !== null && !isNaN(val));
    
    if (values.length === 0) return null;
    
    switch (aggregation.toLowerCase()) {
      case 'sum':
        return values.reduce((a, b) => a + b, 0);
      case 'avg':
      case 'average':
        return values.reduce((a, b) => a + b, 0) / values.length;
      case 'max':
        return Math.max(...values);
      case 'min':
        return Math.min(...values);
      case 'count':
        return values.length;
      case 'count_distinct':
        return new Set(values).size;
      default:
        return null;
    }
  },

  /**
   * Encuentra el schema de una columna (métrica o dimensión)
   * @param {string} columnName - Nombre de la columna
   * @returns {Object|null} Schema de la columna o null si no se encuentra
   */
  findColumnSchema(columnName) {
    if (!this.schema) return null;
    
    // Buscar en métricas
    const metric = this.schema.metrics?.find(m => m.name === columnName);
    if (metric) return metric;
    
    // Buscar en dimensiones
    const dimension = this.schema.dimensions?.find(d => d.name === columnName);
    if (dimension) return dimension;
    
    return null;
  },

  /**
   * Obtiene el label de una columna desde su schema
   * @param {string} columnName - Nombre de la columna
   * @returns {string} Label de la columna o el nombre si no se encuentra
   */
  getColumnLabel(columnName) {
    const schema = this.findColumnSchema(columnName);
    return schema?.label || columnName;
  },

  /**
   * Formatea una métrica de columna según su configuración
   * @param {number} value - Valor a formatear
   * @param {Object} metricConfig - Configuración de la métrica
   * @param {Object} columnSchema - Schema de la columna (opcional)
   * @returns {string} Valor formateado
   */
  formatColumnMetric(value, metricConfig, columnSchema) {
    if (value === null || value === undefined) return "0";
    
    const format = metricConfig.format || "auto";
    
    // Si el formato es "auto", usar el formato del schema de la columna
    if (format === "auto" && columnSchema) {
      return this.formatMetric(value, columnSchema);
    }
    
    // Si no hay schema o el formato es explícito, crear un schema temporal
    const tempSchema = {
      data_type: format === "currency" ? "currency" : 
                 format === "integer" ? "integer" : "number",
      format: format === "currency" ? "currency:ARS:2" : 
              format === "integer" ? "number:0" : "number:2"
    };
    
    return this.formatMetric(value, tempSchema);
  },

  /**
   * Construye el título de una tabla con conteo y métricas de columnas
   * @param {Object} widgetSchema - Schema del widget
   * @param {Array} data - Datos de la tabla
   * @returns {string} Título completo formateado
   */
  buildTableTitle(widgetSchema, data) {
    const baseTitle = widgetSchema.title || "Widget";
    const titleOptions = widgetSchema.options?.title_options || {};
    
    let title = baseTitle;
    
    // Parte 1: Conteo de filas (si está habilitado)
    if (titleOptions.show_count) {
      const count = data.length;
      const countFormat = titleOptions.count_format || "number";
      let countText = String(count);
      
      if (countFormat === "parentheses") {
        countText = `(${countText})`;
      } else if (countFormat === "badge") {
        countText = `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200">${countText}</span>`;
      }
      
      const countSeparator = titleOptions.count_separator || " ";
      const countPosition = titleOptions.count_position || "after";
      
      if (countPosition === "before") {
        title = `${countText}${countSeparator}${title}`;
      } else {
        title = `${title}${countSeparator}${countText}`;
      }
    }
    
    // Parte 2: Métricas de columnas
    if (titleOptions.column_metrics && Array.isArray(titleOptions.column_metrics)) {
      titleOptions.column_metrics.forEach(metricConfig => {
        if (!metricConfig.column || !metricConfig.aggregation) return;
        
        const value = this.calculateColumnAggregation(
          data,
          metricConfig.column,
          metricConfig.aggregation
        );
        
        if (value !== null && value !== undefined) {
          // Obtener schema de la columna para formateo
          const columnSchema = this.findColumnSchema(metricConfig.column);
          
          // Formatear valor
          const formatted = this.formatColumnMetric(
            value,
            metricConfig,
            columnSchema
          );
          
          // Construir etiqueta
          const label = metricConfig.label || 
            `${this.getColumnLabel(metricConfig.column)} (${metricConfig.aggregation})`;
          
          const separator = metricConfig.separator || " | ";
          const metricText = `${label}: ${formatted}`;
          
          const position = metricConfig.position || "after";
          if (position === "before") {
            title = `${metricText}${separator}${title}`;
          } else {
            title = `${title}${separator}${metricText}`;
          }
        }
      });
    }
    
    return title;
  },

  /**
   * Agrupa datos de tabla recursivamente por múltiples campos
   * @param {Array} data - Datos a agrupar
   * @param {Array} groupByFields - Array de nombres de campos por los que agrupar
   * @param {Object} schema - Schema del reporte (para obtener información de campos)
   * @param {Array} totalColumns - Columnas a totalizar
   * @returns {Array} Datos agrupados con estructura {type: 'group'|'item', data: {...}, children: [...]}
   */
  groupTableData(data, groupByFields, schema, totalColumns = []) {
    if (!groupByFields || !Array.isArray(groupByFields) || groupByFields.length === 0 || !data || !data.length) {
      return data;
    }
    
    // Función recursiva para agrupar por múltiples niveles
    const groupByLevels = (items, fields, level = 0) => {
      if (level >= fields.length) {
        // Si no hay más niveles, retornar los items directamente como items finales
        return items.map(item => ({
          type: 'item',
          data: item,
        }));
      }
      
      const currentField = fields[level];
      const grouped = {};
      
      // Agrupar por el campo actual
      items.forEach(row => {
        const rawValue = row[currentField] || "Sin especificar";
        const groupKey = rawValue; // Usar valor original como clave para agrupar
        
        // Formatear el valor para mostrar (si es fecha, usar DD-MM-AAAA)
        let groupValue = rawValue;
        const fieldSchema = schema.dimensions?.find(d => d.name === currentField) || 
                          schema.metrics?.find(m => m.name === currentField);
        if (fieldSchema && (fieldSchema.data_type === 'date' || fieldSchema.data_type === 'datetime')) {
          groupValue = this.formatDateToDDMMYYYY(rawValue);
        }
        
        if (!grouped[groupKey]) {
          grouped[groupKey] = {
            groupKey,
            groupValue: groupValue,
            groupField: currentField,
            items: [],
            totals: {}
          };
        }
        
        grouped[groupKey].items.push(row);
        
        // Calcular totales para cada columna numérica
        totalColumns.forEach(col => {
          if (!grouped[groupKey].totals[col]) {
            grouped[groupKey].totals[col] = 0;
          }
          const value = parseFloat(row[col]);
          if (!isNaN(value)) {
            grouped[groupKey].totals[col] += value;
          }
        });
        
        // Si no hay columnas específicas, totalizar todas las métricas numéricas
        if (totalColumns.length === 0) {
          Object.keys(row).forEach(key => {
            const value = parseFloat(row[key]);
            if (!isNaN(value) && key !== currentField) {
              if (!grouped[groupKey].totals[key]) {
                grouped[groupKey].totals[key] = 0;
              }
              grouped[groupKey].totals[key] += value;
            }
          });
        }
      });
      
      // Función para ordenar claves según el tipo de campo
      const sortKeys = (keys, fieldName) => {
        // Buscar el schema del campo para determinar el tipo
        const fieldSchema = schema.dimensions?.find(d => d.name === fieldName) || 
                          schema.metrics?.find(m => m.name === fieldName);
        
        // Si el campo es fecha, ordenar como fechas
        if (fieldSchema && (fieldSchema.data_type === 'date' || fieldSchema.data_type === 'datetime')) {
          return keys.sort((a, b) => {
            const parseDate = (dateStr) => {
              if (!dateStr || dateStr === "Sin especificar") return new Date(0);
              // Intentar parsear fechas en formato DD/MM/YYYY
              const parts = dateStr.split('/');
              if (parts.length === 3) {
                const day = parseInt(parts[0], 10);
                const month = parseInt(parts[1], 10);
                const year = parseInt(parts[2], 10);
                if (!isNaN(day) && !isNaN(month) && !isNaN(year)) {
                  return new Date(year, month - 1, day);
                }
              }
              // Intentar formato YYYY-MM-DD
              const isoDate = new Date(dateStr);
              if (!isNaN(isoDate.getTime())) {
                return isoDate;
              }
              return new Date(0);
            };
            
            const dateA = parseDate(a);
            const dateB = parseDate(b);
            return dateA - dateB;
          });
        }
        // Para otros campos, ordenar alfabéticamente
        return keys.sort();
      };
      
      // Convertir a array y procesar cada grupo recursivamente
      const result = [];
      sortKeys(Object.keys(grouped), currentField).forEach(key => {
        const group = grouped[key];
        // Agrupar los items de este grupo por el siguiente nivel
        const nestedGroups = groupByLevels(group.items, fields, level + 1);
        
        result.push({
          type: 'group',
          data: {
            ...group,
            items: [], // Siempre vacío - los items están en children
          },
          children: nestedGroups,
        });
      });
      
      return result;
    };
    
    return groupByLevels(data, groupByFields);
  },

  /**
   * Renderiza una tabla de datos
   * @param {HTMLElement} container - Contenedor del widget
   * @param {Object} widgetSchema - Schema del widget
   */
  renderTable(container, widgetSchema) {
    const data = this.queryResult.data || [];
    const dimensions = this.schema.dimensions || [];
    const metrics = this.schema.metrics || [];

    if (data.length === 0) {
      container.className = "p-6";
      container.innerHTML = `<p class="text-sm text-slate-500 dark:text-slate-400 text-center">No hay datos disponibles</p>`;
      return;
    }

    // Si el widget tiene columnas personalizadas definidas, usarlas
    let filteredDimensions = dimensions;
    let filteredMetrics = metrics;
    
    // Para dimensiones: si table_dimensions está definido (incluso si está vacío), usar solo las seleccionadas
    if (widgetSchema.options?.table_dimensions !== undefined && Array.isArray(widgetSchema.options.table_dimensions)) {
      if (widgetSchema.options.table_dimensions.length > 0) {
        // Filtrar dimensiones según las seleccionadas en el widget
        filteredDimensions = dimensions.filter(dim => widgetSchema.options.table_dimensions.includes(dim.name));
      } else {
        // Si está definido pero vacío, no mostrar ninguna dimensión
        filteredDimensions = [];
      }
    } else {
      // Si no está definido, usar comportamiento por defecto (filtrar algunas dimensiones)
      const excludedDimensions = ["mes", "id_sucursal", "id_punto_venta"];
      if (this.reportSlug === "pedidos-pendientes") {
        excludedDimensions.push("tipo_comprobante", "estado");
      }
      filteredDimensions = dimensions.filter((dim) => {
        const dimName = dim.name.toLowerCase();
        return !excludedDimensions.includes(dimName);
      });
    }

    // Pedidos pendientes: nunca mostrar tipo/estado (aunque table_dimensions del Builder aún los liste).
    if (this.reportSlug === "pedidos-pendientes") {
      const ocultarPedidos = new Set(["tipo_comprobante", "estado"]);
      filteredDimensions = filteredDimensions.filter((d) => !ocultarPedidos.has(d.name));
    }
    
    // Para métricas: si table_metrics está definido (incluso si está vacío), usar solo las seleccionadas
    // IMPORTANTE: Para widgets de tipo tabla, si no hay métricas seleccionadas, no mostrar ninguna
    if (widgetSchema.options?.table_metrics !== undefined && Array.isArray(widgetSchema.options.table_metrics)) {
      if (widgetSchema.options.table_metrics.length > 0) {
        // Filtrar métricas según las seleccionadas en el widget
        filteredMetrics = metrics.filter(metric => widgetSchema.options.table_metrics.includes(metric.name));
      } else {
        // Si está definido pero vacío, no mostrar ninguna métrica
        filteredMetrics = [];
      }
    } else {
      // Si table_metrics no está definido, verificar si es un widget de tabla
      // Para widgets de tabla sin table_metrics definido, asumir que no hay métricas seleccionadas
      if (widgetSchema.kind === 'table') {
        // Para widgets de tabla sin table_metrics definido, no mostrar métricas
        // (el usuario debe seleccionarlas explícitamente en el builder)
        filteredMetrics = [];
      } else {
        // Para otros tipos de widgets (gráficos), usar comportamiento por defecto
        // IMPORTANTE: Excluir métricas personalizadas de otros widgets
        const customWidgetMetrics = this.schema.options?.custom_widget_metrics || [];
        filteredMetrics = metrics.filter(metric => {
          // Excluir métricas personalizadas de otros widgets
          return !customWidgetMetrics.includes(metric.name);
        });
      }
    }

    // Mapear labels: renombrar "mes_formato" a "MES"
    const mappedDimensions = filteredDimensions.map(dim => {
      const mappedDim = { ...dim };
      if (dim.name.toLowerCase() === "mes_formato") {
        mappedDim.label = "MES";
      }
      return mappedDim;
    });

    // Dimensiones permitidas en "Agrupar por": si el Builder guardó grouping.fields no vacío,
    // solo esas (intersectadas con columnas de la tabla); si no queda ninguna, se muestran todas.
    let dimensionsForGroupBySelect = mappedDimensions.filter((d) => {
      if (this.reportSlug === "pedidos-pendientes") {
        if (d.name === "tipo_comprobante" || d.name === "estado") return false;
      }
      return true;
    });
    const groupingFieldsAllow = widgetSchema.options?.grouping?.fields;
    if (Array.isArray(groupingFieldsAllow) && groupingFieldsAllow.length > 0) {
      const allow = new Set(groupingFieldsAllow);
      const narrowed = dimensionsForGroupBySelect.filter((d) => allow.has(d.name));
      if (narrowed.length > 0) {
        dimensionsForGroupBySelect = narrowed;
      }
    }

    // Detectar si estamos en workspace
    const isWorkspace = this.rootElement?.closest("[data-workspace-mode]") || 
                        this.rootElement?.closest("[data-widget-id]")?.closest("[data-workspace-mode]");
    
    // Detectar si estamos en modo TV (workspace TV)
    const isWorkspaceTV = this.rootElement?.closest("[data-workspace-tv]") || 
                          this.rootElement?.closest("[data-widget-id]")?.closest("[data-workspace-tv]") ||
                          document.querySelector("[data-workspace-tv]");
    
    // Aplicar padding según el contexto (workspace usa menos padding, TV usa flexbox)
    if (isWorkspaceTV) {
      // En modo TV, usar flexbox para que la tabla ocupe todo el espacio
      container.className = "flex flex-col h-full";
    } else if (isWorkspace) {
      container.className = "p-3 sm:p-4";
    } else {
      container.className = "p-4 sm:p-6";
    }
    
    // Verificar si hay agrupación configurada (definir antes de usarla)
    const groupingConfig = widgetSchema.options?.grouping;

    const pickableGroupNames = new Set(dimensionsForGroupBySelect.map((d) => d.name));
    const persistenceWidgetId = String(
      widgetSchema.id != null && widgetSchema.id !== "" ? widgetSchema.id : "default"
    );
    const storageState = this._loadTableGroupingStorageState(this.reportSlug, persistenceWidgetId);
    let initialGroupFields = [];
    if (storageState.used) {
      initialGroupFields = storageState.fields.filter((f) => pickableGroupNames.has(f));
    } else if (
      groupingConfig?.enabled &&
      Array.isArray(groupingConfig.fields) &&
      groupingConfig.fields.length > 0
    ) {
      initialGroupFields = groupingConfig.fields.filter((f) => pickableGroupNames.has(f));
    }

    // ID estable para DOM y localStorage (sin caracteres inválidos en id HTML)
    const domSafeWidgetId = persistenceWidgetId.replace(/[^a-zA-Z0-9_-]/g, "_");
    const groupByFieldId = `table-group-by-${domSafeWidgetId}`;
    
    // Controles de agrupación dinámica - SOLO mostrar si NO estamos en workspace
    let groupingControlsHTML = '';
    if (!isWorkspace) {
      groupingControlsHTML += `
        <div class="mb-4 space-y-3 border-b border-slate-200 dark:border-slate-700 pb-4">
          <div class="flex flex-col gap-2">
            <label class="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Agrupar por
            </label>
            <div class="relative">
              <select name="group_by"
                      id="${groupByFieldId}"
                      multiple
                      class="hidden"
                      data-tags-field="group_by">
      `;
      
      dimensionsForGroupBySelect.forEach((dim) => {
        const isSelected = initialGroupFields.includes(dim.name);
        groupingControlsHTML += `<option value="${dim.name}" ${isSelected ? 'selected' : ''}>${dim.label}</option>`;
      });
      
      groupingControlsHTML += `
              </select>
              <div id="${groupByFieldId}_tags_container" 
                   class="tags-filter-container flex flex-wrap items-center gap-1.5 py-2 px-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md min-h-[2.5rem] focus-within:ring-2 focus-within:ring-sky-400 focus-within:border-sky-400 transition-all duration-300">
                <div class="tags-chips flex flex-wrap gap-1.5 flex-1"></div>
                <input type="text"
                       id="${groupByFieldId}_search"
                       class="tags-input flex-1 min-w-[120px] bg-transparent border-none outline-none text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500"
                       placeholder="Buscar campo de agrupación..."
                       autocomplete="off">
                <div id="${groupByFieldId}_dropdown" class="tags-dropdown absolute top-full left-0 right-0 z-50 mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shadow-lg max-h-60 overflow-y-auto hidden"></div>
              </div>
            </div>
            <span class="text-[10px] font-normal text-slate-400 dark:text-slate-500 italic">Puedes seleccionar múltiples campos para agrupar (ej: Fecha y Cliente/Proveedor). El orden determina los niveles de agrupación.</span>
          </div>
        </div>
      `;
    }
    
    // En modo TV, el wrapper de la tabla debe usar flex para ocupar todo el espacio
    const tableWrapperClass = isWorkspaceTV ? "flex-1 overflow-auto" : "overflow-x-auto";
    
    let tableHTML = `
      <div class="${tableWrapperClass}">
        <table class="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
          <thead class="bg-slate-50 dark:bg-slate-800">
            <tr>
    `;

    // Encabezados de dimensiones (filtradas y mapeadas)
    mappedDimensions.forEach(dim => {
      // Si la dimensión es numérica (tiene formato o data_type numérico), alinear a la derecha
      const isNumeric = dim.data_type === "integer" || dim.data_type === "number" || dim.format;
      const alignClass = isNumeric ? "text-right" : "text-left";
      tableHTML += `<th class="px-4 py-2 ${alignClass} text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">${dim.label}</th>`;
    });

    // Encabezados de métricas (filtradas)
    filteredMetrics.forEach(metric => {
      tableHTML += `<th class="px-4 py-2 text-right text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">${metric.label}</th>`;
    });

    tableHTML += `
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-slate-900 divide-y divide-slate-200 dark:divide-slate-700">
    `;

    const isGrouped = initialGroupFields.length > 0;
    
    let rowsHTML = '';
    
    if (isGrouped) {
      // Agrupar datos
      let totalColumns = [];
      if (groupingConfig.total_columns && groupingConfig.total_columns.length > 0) {
        // Usar las columnas especificadas (pueden ser métricas o dimensiones numéricas)
        totalColumns = groupingConfig.total_columns;
      } else {
        // Si no hay columnas específicas, totalizar todas las métricas numéricas
        // y dimensiones numéricas
        totalColumns = filteredMetrics.map(m => m.name);
        // Agregar dimensiones numéricas
        mappedDimensions.forEach(dim => {
          const isNumeric = dim.data_type === "integer" || dim.data_type === "number" || dim.format;
          if (isNumeric) {
            totalColumns.push(dim.name);
          }
        });
      }
      
      const groupedData = this.groupTableData(data, initialGroupFields, this.schema, totalColumns);
      
      // Renderizar con grupos
      rowsHTML = this.renderGroupedTableRows(
        groupedData, 
        mappedDimensions, 
        filteredMetrics, 
        groupingConfig.collapsed_by_default !== false,
        0,
        null
      );
    } else {
      // Filas de datos sin agrupación
    data.forEach((row, index) => {
      const rowClass = index % 2 === 0 ? "bg-white dark:bg-slate-900" : "bg-slate-50 dark:bg-slate-800";
        rowsHTML += `<tr class="${rowClass}">`;

      // Celdas de dimensiones (usar dimensiones filtradas y mapeadas)
      mappedDimensions.forEach(dim => {
        const value = row[dim.name];
        const formatted = this.formatDimension(value, dim);
          // Si la dimensión es numérica (tiene formato o data_type numérico), alinear a la derecha
          const isNumeric = dim.data_type === "integer" || dim.data_type === "number" || dim.format;
          const alignClass = isNumeric ? "text-right" : "text-left";
          rowsHTML += `<td class="px-4 py-2 text-xs text-slate-900 dark:text-slate-100 ${alignClass}">${formatted}</td>`;
        });

        // Celdas de métricas (filtradas)
        filteredMetrics.forEach(metric => {
          const value = row[metric.name];
          const formatted = this.formatMetric(value, metric);
          rowsHTML += `<td class="px-4 py-2 text-xs text-slate-900 dark:text-slate-100 text-right">${formatted}</td>`;
        });

        rowsHTML += `</tr>`;
      });
    }
    
    tableHTML += rowsHTML;

    tableHTML += `
          </tbody>
        </table>
      </div>
    `;

    // Combinar controles de agrupación y tabla
    container.innerHTML = groupingControlsHTML + tableHTML;
    
    // Aplicar altura para tablas en workspace
    if (isWorkspace) {
      const tableWrapper = container.querySelector('.overflow-x-auto, .overflow-auto');
      if (tableWrapper) {
        if (isWorkspaceTV) {
          // En modo TV, la tabla debe usar todo el espacio disponible (flex-1 ya aplicado)
          // No establecer altura fija, dejar que flex maneje el espacio
          tableWrapper.style.minHeight = "0"; // Importante para que flex funcione correctamente
        } else {
          // Para reportes de tabla en workspace normal, aplicar altura fija de 288px (5 filas visibles)
          tableWrapper.style.height = "288px";
          tableWrapper.style.minHeight = "288px";
          tableWrapper.style.maxHeight = "288px";
          tableWrapper.style.overflowY = "auto";
          tableWrapper.style.overflowX = "auto";
        }
      }
    }
    
    // Inicializar controles de agrupación dinámica SOLO si NO estamos en workspace
    if (!isWorkspace) {
      setTimeout(() => {
        this.initializeTableGroupingControls(
          groupByFieldId,
          widgetSchema,
          data,
          mappedDimensions,
          filteredMetrics,
          container,
          dimensionsForGroupBySelect,
          initialGroupFields,
          persistenceWidgetId
        );
      }, 100);
    }
    
    // Si hay agrupación, agregar event listeners para expandir/colapsar
    // PERO NO en workspace (agrupación deshabilitada en workspace)
    if (isGrouped && !isWorkspace) {
      this.attachGroupToggleListeners(container);
    }
  },

  /**
   * Inicializa los controles de agrupación dinámica para una tabla
   * @param {string} fieldId - ID del campo de agrupación
   * @param {Object} widgetSchema - Schema del widget
   * @param {Array} data - Datos de la tabla
   * @param {Array} dimensions - Dimensiones de la tabla (mapeadas)
   * @param {Array} metrics - Métricas disponibles
   * @param {HTMLElement} container - Contenedor del widget
   * @param {Array} [dimensionsForGroupBySelect] - Subconjunto permitido en "Agrupar por" (Builder grouping.fields)
   * @param {string[]} [initialGroupFields] - Campos iniciales (schema + localStorage ya resueltos en renderTable)
   * @param {string} persistenceWidgetId - Id estable del widget para localStorage
   */
  initializeTableGroupingControls(
    fieldId,
    widgetSchema,
    data,
    dimensions,
    metrics,
    container,
    dimensionsForGroupBySelect = null,
    initialGroupFields = null,
    persistenceWidgetId = "default"
  ) {
    const select = document.getElementById(fieldId);
    const tagsContainer = document.getElementById(`${fieldId}_tags_container`);
    const chipsContainer = tagsContainer?.querySelector(".tags-chips");
    const input = document.getElementById(`${fieldId}_search`);
    const dropdown = document.getElementById(`${fieldId}_dropdown`);
    
    if (!select || !tagsContainer || !chipsContainer || !input || !dropdown) {
      return;
    }
    
    // Evitar múltiples inicializaciones
    if (tagsContainer.dataset.initialized === "true") {
      return;
    }
    tagsContainer.dataset.initialized = "true";
    
    let allOptions = [];
    let selectedValues = new Set();
    let selectedIndex = -1;
    
    const dimsForPicker =
      Array.isArray(dimensionsForGroupBySelect) && dimensionsForGroupBySelect.length > 0
        ? dimensionsForGroupBySelect
        : dimensions;
    dimsForPicker.forEach((dim) => {
      allOptions.push({ value: dim.name, label: dim.label });
    });
    
    const groupingConfig = widgetSchema.options?.grouping;
    // Si initialGroupFields es array (puede ser [] por localStorage), no volver al schema.
    const seedFields = Array.isArray(initialGroupFields)
      ? initialGroupFields
      : groupingConfig?.enabled && Array.isArray(groupingConfig.fields)
        ? groupingConfig.fields
        : [];
    seedFields.forEach((field) => {
      if (!dimsForPicker.some((d) => d.name === field)) return;
      selectedValues.add(field);
      const option = select.querySelector(`option[value="${field}"]`);
      if (option) option.selected = true;
    });
    
    // Renderizar chips seleccionados
    const renderChips = () => {
      chipsContainer.innerHTML = "";
      selectedValues.forEach((value) => {
        const option = allOptions.find((opt) => opt.value === value);
        if (option) {
          const chip = document.createElement("div");
          chip.className = "inline-flex items-center gap-1 px-2 py-1 bg-sky-100 dark:bg-sky-900 text-sky-800 dark:text-sky-200 rounded-full text-xs font-medium";
          chip.dataset.value = value;
          
          const chipText = document.createElement("span");
          chipText.textContent = option.label;
          chip.appendChild(chipText);
          
          const chipRemove = document.createElement("button");
          chipRemove.type = "button";
          chipRemove.className = "ml-1 hover:text-sky-600 dark:hover:text-sky-300 focus:outline-none";
          chipRemove.innerHTML = "×";
          chipRemove.addEventListener("click", (e) => {
            e.stopPropagation();
            removeTag(value);
          });
          chip.appendChild(chipRemove);
          
          chipsContainer.appendChild(chip);
        }
      });
    };
    
    // Agregar tag
    const addTag = (value) => {
      if (!selectedValues.has(value)) {
        selectedValues.add(value);
        const option = select.querySelector(`option[value="${value}"]`);
        if (option) {
          option.selected = true;
        }
        renderChips();
        input.value = "";
        hideDropdown();
        updateGrouping();
      }
    };
    
    // Remover tag
    const removeTag = (value) => {
      selectedValues.delete(value);
      const option = select.querySelector(`option[value="${value}"]`);
      if (option) {
        option.selected = false;
      }
      renderChips();
      updateGrouping();
    };
    
    // Actualizar agrupación y re-renderizar tabla
    const updateGrouping = () => {
      const groupByFields = Array.from(selectedValues);
      this._savePersistedTableGrouping(this.reportSlug, persistenceWidgetId, groupByFields);
      this.renderTableWithGrouping(container, widgetSchema, data, dimensions, metrics, groupByFields);
    };
    
    // Mostrar dropdown
    const showDropdown = () => {
      dropdown.classList.remove("hidden");
    };
    
    // Ocultar dropdown
    const hideDropdown = () => {
      dropdown.classList.add("hidden");
      selectedIndex = -1;
    };
    
    // Renderizar dropdown
    const renderDropdown = (results, query) => {
      dropdown.innerHTML = "";
      
      if (results.length === 0) {
        const noResults = document.createElement("div");
        noResults.className = "px-3 py-2 text-xs text-slate-500 dark:text-slate-400";
        noResults.textContent = query ? "No se encontraron resultados" : "Escribe para buscar...";
        dropdown.appendChild(noResults);
        return;
      }
      
      results.forEach((item, index) => {
        const isSelected = selectedValues.has(item.value);
        const itemDiv = document.createElement("div");
        itemDiv.className = `px-3 py-2 text-xs cursor-pointer transition-colors ${
          index === selectedIndex
            ? "bg-sky-100 dark:bg-sky-900"
            : "hover:bg-slate-100 dark:hover:bg-slate-700"
        } ${isSelected ? "bg-sky-50 dark:bg-sky-950" : ""}`;
        itemDiv.dataset.value = item.value;
        
        const itemContent = document.createElement("div");
        itemContent.className = "flex items-center justify-between";
        
        const itemLabel = document.createElement("span");
        itemLabel.className = isSelected ? "font-medium text-sky-700 dark:text-sky-300" : "text-slate-700 dark:text-slate-300";
        itemLabel.textContent = item.label;
        itemContent.appendChild(itemLabel);
        
        if (isSelected) {
          const checkIcon = document.createElement("span");
          checkIcon.className = "text-sky-600 dark:text-sky-400";
          checkIcon.innerHTML = "✓";
          itemContent.appendChild(checkIcon);
        }
        
        itemDiv.appendChild(itemContent);
        
        itemDiv.addEventListener("click", () => {
          if (isSelected) {
            removeTag(item.value);
          } else {
            addTag(item.value);
          }
        });
        
        dropdown.appendChild(itemDiv);
      });
    };
    
    // Búsqueda en el input
    input.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase().trim();
      
      if (query.length === 0) {
        renderDropdown(allOptions.filter(opt => !selectedValues.has(opt.value)), "");
        showDropdown();
        return;
      }
      
      const filtered = allOptions.filter(opt => {
        const matchesQuery = opt.label.toLowerCase().includes(query) || 
                            opt.value.toLowerCase().includes(query);
        return matchesQuery && !selectedValues.has(opt.value);
      });
      
      renderDropdown(filtered, query);
      showDropdown();
    });
    
    input.addEventListener("focus", () => {
      if (input.value.length === 0) {
        renderDropdown(allOptions.filter(opt => !selectedValues.has(opt.value)), "");
        showDropdown();
      }
    });
    
    // Navegación por teclado
    input.addEventListener("keydown", (e) => {
      const items = dropdown.querySelectorAll("div[data-value]");
      
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (input.value.length === 0) {
          renderDropdown(allOptions.filter(opt => !selectedValues.has(opt.value)), "");
          showDropdown();
        }
        selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
        items[selectedIndex]?.scrollIntoView({ block: "nearest" });
        items.forEach((item, idx) => {
          item.className = item.className.replace("bg-sky-100 dark:bg-sky-900", "");
          if (idx === selectedIndex) {
            item.className += " bg-sky-100 dark:bg-sky-900";
          }
        });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        if (selectedIndex >= 0) {
          items[selectedIndex]?.scrollIntoView({ block: "nearest" });
          items.forEach((item, idx) => {
            item.className = item.className.replace("bg-sky-100 dark:bg-sky-900", "");
            if (idx === selectedIndex) {
              item.className += " bg-sky-100 dark:bg-sky-900";
            }
          });
        }
      } else if (e.key === "Enter" && selectedIndex >= 0 && items[selectedIndex]) {
        e.preventDefault();
        const value = items[selectedIndex].dataset.value;
        addTag(value);
      } else if (e.key === "Escape") {
        hideDropdown();
      }
    });
    
    // Ocultar dropdown al hacer clic fuera
    document.addEventListener("click", (e) => {
      if (!tagsContainer.contains(e.target)) {
        hideDropdown();
      }
    });
    
    // Renderizar chips iniciales
    renderChips();
  },

  /**
   * Re-renderiza una tabla con agrupación específica
   * @param {HTMLElement} container - Contenedor del widget
   * @param {Object} widgetSchema - Schema del widget
   * @param {Array} data - Datos de la tabla
   * @param {Array} dimensions - Dimensiones disponibles
   * @param {Array} metrics - Métricas disponibles
   * @param {Array} groupByFields - Campos por los que agrupar
   */
  renderTableWithGrouping(container, widgetSchema, data, dimensions, metrics, groupByFields) {
    // Preservar los controles de agrupación
    const groupingControls = container.querySelector('[class*="tags-filter-container"]')?.parentElement?.parentElement;
    
    // Limpiar solo la tabla (preservar controles)
    const tableWrapper = container.querySelector('.overflow-x-auto');
    if (tableWrapper) {
      tableWrapper.remove();
    }
    
    // Construir nueva tabla
    let tableHTML = `
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
          <thead class="bg-slate-50 dark:bg-slate-800">
            <tr>
    `;
    
    // Encabezados de dimensiones
    dimensions.forEach(dim => {
      const isNumeric = dim.data_type === "integer" || dim.data_type === "number" || dim.format;
      const alignClass = isNumeric ? "text-right" : "text-left";
      tableHTML += `<th class="px-4 py-2 ${alignClass} text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">${dim.label}</th>`;
    });
    
    // Encabezados de métricas
    metrics.forEach(metric => {
      tableHTML += `<th class="px-4 py-2 text-right text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">${metric.label}</th>`;
    });
    
    tableHTML += `
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-slate-900 divide-y divide-slate-200 dark:divide-slate-700">
    `;
    
    // Verificar si hay agrupación
    const isGrouped = Array.isArray(groupByFields) && groupByFields.length > 0;
    let rowsHTML = '';
    
    if (isGrouped) {
      // Calcular columnas a totalizar
      const groupingConfig = widgetSchema.options?.grouping || {};
      let totalColumns = [];
      if (groupingConfig.total_columns && groupingConfig.total_columns.length > 0) {
        totalColumns = groupingConfig.total_columns;
      } else {
        totalColumns = metrics.map(m => m.name);
        dimensions.forEach(dim => {
          const isNumeric = dim.data_type === "integer" || dim.data_type === "number" || dim.format;
          if (isNumeric) {
            totalColumns.push(dim.name);
          }
        });
      }
      
      const groupedData = this.groupTableData(data, groupByFields, this.schema, totalColumns);
      
      rowsHTML = this.renderGroupedTableRows(
        groupedData,
        dimensions,
        metrics,
        groupingConfig.collapsed_by_default !== false,
        0,
        null
      );
    } else {
      // Filas sin agrupación
      data.forEach((row, index) => {
        const rowClass = index % 2 === 0 ? "bg-white dark:bg-slate-900" : "bg-slate-50 dark:bg-slate-800";
        rowsHTML += `<tr class="${rowClass}">`;
        
        dimensions.forEach(dim => {
          const value = row[dim.name];
          const formatted = this.formatDimension(value, dim);
          const isNumeric = dim.data_type === "integer" || dim.data_type === "number" || dim.format;
          const alignClass = isNumeric ? "text-right" : "text-left";
          rowsHTML += `<td class="px-4 py-2 text-xs text-slate-900 dark:text-slate-100 ${alignClass}">${formatted}</td>`;
        });
        
      metrics.forEach(metric => {
        const value = row[metric.name];
        const formatted = this.formatMetric(value, metric);
          rowsHTML += `<td class="px-4 py-2 text-xs text-slate-900 dark:text-slate-100 text-right">${formatted}</td>`;
      });

        rowsHTML += `</tr>`;
    });
    }

    tableHTML += rowsHTML;
    tableHTML += `
          </tbody>
        </table>
      </div>
    `;

    // Insertar la nueva tabla después de los controles
    if (groupingControls) {
      groupingControls.insertAdjacentHTML('afterend', tableHTML);
    } else {
      container.insertAdjacentHTML('beforeend', tableHTML);
    }
    
    // Agregar event listeners para expandir/colapsar si hay agrupación
    if (isGrouped) {
      this.attachGroupToggleListeners(container);
    }
  },

  /**
   * Renderiza filas de tabla con grupos anidados
   * @param {Array} groupedData - Datos agrupados
   * @param {Array} dimensions - Dimensiones a mostrar
   * @param {Array} metrics - Métricas a mostrar
   * @param {boolean} collapsedByDefault - Si los grupos inician colapsados
   * @param {number} level - Nivel de anidación actual
   * @param {string} parentId - ID del grupo padre
   * @returns {string} HTML de las filas renderizadas
   */
  renderGroupedTableRows(groupedData, dimensions, metrics, collapsedByDefault, level = 0, parentId = null) {
    let rowsHTML = '';
    groupedData.forEach((item, index) => {
      if (item.type === 'group') {
        const group = item.data;
        const groupId = `group-${level}-${group.groupKey}-${Math.random().toString(36).substr(2, 9)}`;
        const isCollapsed = collapsedByDefault;
        
        // Colores diferentes según el nivel de anidación
        let bgClass = "bg-slate-100 dark:bg-slate-800";
        if (level === 1) {
          bgClass = "bg-slate-50 dark:bg-slate-900";
        } else if (level >= 2) {
          bgClass = "bg-slate-25 dark:bg-slate-850";
        }
        
        const paddingLeft = level > 0 ? `${level * 16 + 16}px` : '16px';
        const displayStyle = isCollapsed && parentId ? 'display: none;' : '';
        
        // Obtener label del campo de agrupación
        const groupFieldSchema = dimensions.find(d => d.name === group.groupField) || 
                                 { label: group.groupField.replace(/_/g, " ").toUpperCase() };
        const groupLabel = groupFieldSchema.label;
        const groupValue = group.groupValue || "Sin especificar";
        
        // Icono de expandir/colapsar
        const expandIcon = `<svg class="w-4 h-4 inline-block mr-2 transition-transform group-toggle-icon" style="transform: ${isCollapsed ? 'rotate(0deg)' : 'rotate(90deg)'};" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M9 18l6-6-6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;
        
        // Totales del grupo
        let totalsHTML = '';
        if (group.totals && Object.keys(group.totals).length > 0) {
          const totalsArray = [];
          Object.keys(group.totals).forEach(col => {
            // Buscar primero en métricas
            let fieldSchema = metrics.find(m => m.name === col);
            let fieldLabel = fieldSchema?.label || col;
            let formattedValue;
            let valueColorClass = '';
            
            if (fieldSchema) {
              // Es una métrica, usar formatMetric
              const totalValue = group.totals[col];
              formattedValue = this.formatMetric(totalValue, fieldSchema);
              
              // Determinar color según el valor y tipo de campo
              if (fieldSchema.data_type === "currency" || fieldSchema.format?.startsWith("currency")) {
                // Para moneda: verde si positivo, rojo si negativo
                if (totalValue > 0) {
                  valueColorClass = 'text-emerald-600 dark:text-emerald-400 font-semibold';
                } else if (totalValue < 0) {
                  valueColorClass = 'text-rose-600 dark:text-rose-400 font-semibold';
                } else {
                  valueColorClass = 'text-slate-600 dark:text-slate-400';
                }
              } else if (fieldSchema.data_type === "integer" || fieldSchema.data_type === "number") {
                // Para números: azul destacado
                valueColorClass = 'text-sky-600 dark:text-sky-400 font-semibold';
              } else {
                valueColorClass = 'text-slate-600 dark:text-slate-400';
              }
            } else {
              // Buscar en dimensiones numéricas
              fieldSchema = dimensions.find(d => d.name === col);
              if (fieldSchema) {
                fieldLabel = fieldSchema.label || col;
                const totalValue = group.totals[col];
                // Si es numérico, formatear como métrica
                const isNumeric = fieldSchema.data_type === "integer" || 
                                fieldSchema.data_type === "number" || 
                                fieldSchema.format;
                if (isNumeric) {
                  // Crear un schema temporal para formatear
                  const metricSchema = {
                    data_type: fieldSchema.data_type || "number",
                    format: fieldSchema.format
                  };
                  formattedValue = this.formatMetric(totalValue, metricSchema);
                  
                  // Determinar color según el valor y tipo de campo
                  if (fieldSchema.format?.startsWith("currency") || fieldSchema.data_type === "currency") {
                    // Para moneda: verde si positivo, rojo si negativo
                    if (totalValue > 0) {
                      valueColorClass = 'text-emerald-600 dark:text-emerald-400 font-semibold';
                    } else if (totalValue < 0) {
                      valueColorClass = 'text-rose-600 dark:text-rose-400 font-semibold';
                    } else {
                      valueColorClass = 'text-slate-600 dark:text-slate-400';
                    }
                  } else {
                    // Para números: azul destacado
                    valueColorClass = 'text-sky-600 dark:text-sky-400 font-semibold';
                  }
                } else {
                  formattedValue = String(totalValue);
                  valueColorClass = 'text-slate-600 dark:text-slate-400';
                }
              } else {
                // Campo no encontrado, usar valor numérico formateado
                const totalValue = group.totals[col];
                formattedValue = this.formatNumber(totalValue, 2);
                valueColorClass = 'text-sky-600 dark:text-sky-400 font-semibold';
              }
            }
            
            if (formattedValue !== undefined) {
              totalsArray.push(`<span class="text-slate-600 dark:text-slate-400">${fieldLabel}:</span> <span class="${valueColorClass}">${formattedValue}</span>`);
            }
          });
          if (totalsArray.length > 0) {
            totalsHTML = `<span class="text-xs font-normal ml-4">${totalsArray.join(' <span class="text-slate-400 dark:text-slate-500">|</span> ')}</span>`;
          }
        }
        
        rowsHTML += `
          <tr class="${bgClass} font-semibold border-t-2 border-slate-300 dark:border-slate-600 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors group-row" 
              data-group-id="${groupId}" 
              data-level="${level}" 
              data-parent-id="${parentId || ''}" 
              data-is-collapsed="${isCollapsed}"
              style="${displayStyle}">
            <td colspan="${dimensions.length + metrics.length}" class="px-4 py-3 text-slate-900 dark:text-white" style="padding-left: ${paddingLeft};">
              <div class="flex items-center justify-between">
                <span class="font-semibold flex items-center">
                  ${expandIcon}
                  ${groupLabel}: <span class="font-normal">${groupValue}</span>
                </span>
                ${totalsHTML}
              </div>
            </td>
          </tr>
        `;
        
        // Renderizar hijos recursivamente
        if (item.children && item.children.length > 0) {
          rowsHTML += this.renderGroupedTableRows(
            item.children, 
            dimensions, 
            metrics, 
            collapsedByDefault, 
            level + 1, 
            groupId
          );
        }
      } else if (item.type === 'item') {
        // Renderizar fila normal
        const row = item.data;
        const rowClass = index % 2 === 0 ? "bg-white dark:bg-slate-900" : "bg-slate-50 dark:bg-slate-800";
        const displayStyle = collapsedByDefault && parentId ? 'display: none;' : '';
        const paddingLeft = level > 0 ? `${level * 16 + 16}px` : '16px';
        
        rowsHTML += `<tr class="${rowClass} hover:bg-slate-50/70 dark:hover:bg-slate-900/60 transition-colors item-row" 
                          data-parent-id="${parentId || ''}" 
                          style="${displayStyle}">`;

        // Celdas de dimensiones
        dimensions.forEach((dim, dimIndex) => {
          const value = row[dim.name];
          const formatted = this.formatDimension(value, dim);
          const isNumeric = dim.data_type === "integer" || dim.data_type === "number" || dim.format;
          const alignClass = isNumeric ? "text-right" : "text-left";
          const cellPadding = dimIndex === 0 ? `padding-left: ${paddingLeft};` : '';
          rowsHTML += `<td class="px-4 py-2 text-xs text-slate-900 dark:text-slate-100 ${alignClass}" style="${cellPadding}">${formatted}</td>`;
        });

        // Celdas de métricas
        metrics.forEach(metric => {
          const value = row[metric.name];
          const formatted = this.formatMetric(value, metric);
          rowsHTML += `<td class="px-4 py-2 text-xs text-slate-900 dark:text-slate-100 text-right">${formatted}</td>`;
        });

        rowsHTML += `</tr>`;
      }
    });
    
    return rowsHTML;
  },

  /**
   * Agrega event listeners para expandir/colapsar grupos
   * @param {HTMLElement} container - Contenedor de la tabla
   */
  attachGroupToggleListeners(container) {
    const groupRows = container.querySelectorAll('.group-row');
    
    groupRows.forEach(groupRow => {
      groupRow.addEventListener('click', (e) => {
        e.stopPropagation();
        const groupId = groupRow.dataset.groupId;
        const isCollapsed = groupRow.dataset.isCollapsed === 'true';
        const children = container.querySelectorAll(`[data-parent-id="${groupId}"]`);
        
        if (isCollapsed) {
          // Expandir: mostrar solo hijos directos
          children.forEach(child => {
            if (child.dataset.parentId === groupId) {
              child.style.display = '';
            }
          });
          groupRow.dataset.isCollapsed = 'false';
          const icon = groupRow.querySelector('.group-toggle-icon');
          if (icon) {
            icon.style.transform = 'rotate(90deg)';
          }
        } else {
          // Colapsar: ocultar hijos (recursivamente)
          const collapseChildren = (parentId) => {
            const directChildren = container.querySelectorAll(`[data-parent-id="${parentId}"]`);
            directChildren.forEach(child => {
              if (child.dataset.groupId) {
                // Es un grupo, colapsarlo también
                child.dataset.isCollapsed = 'true';
                const childIcon = child.querySelector('.group-toggle-icon');
                if (childIcon) {
                  childIcon.style.transform = 'rotate(0deg)';
                }
                collapseChildren(child.dataset.groupId);
              }
              child.style.display = 'none';
            });
          };
          collapseChildren(groupId);
          groupRow.dataset.isCollapsed = 'true';
          const icon = groupRow.querySelector('.group-toggle-icon');
          if (icon) {
            icon.style.transform = 'rotate(0deg)';
          }
        }
      });
    });
  },

  /**
   * Formatea una fecha al formato DD-MM-AAAA
   * @param {string|Date} dateValue - Valor de fecha (string o Date)
   * @returns {string} Fecha formateada como DD-MM-AAAA
   */
  formatDateToDDMMYYYY(dateValue) {
    if (!dateValue) return "-";
    
    let date;
    
    // Si es string, intentar parsearlo
    if (typeof dateValue === 'string') {
      // Intentar formato YYYY-MM-DD
      const isoMatch = dateValue.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (isoMatch) {
        const [, year, month, day] = isoMatch;
        date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
      } else {
        // Intentar formato DD/MM/YYYY
        const slashMatch = dateValue.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
        if (slashMatch) {
          const [, day, month, year] = slashMatch;
          date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        } else {
          // Intentar parsear como fecha ISO
          date = new Date(dateValue);
        }
      }
    } else if (dateValue instanceof Date) {
      date = dateValue;
    } else {
      return String(dateValue);
    }
    
    if (isNaN(date.getTime())) {
      return String(dateValue);
    }
    
    // Formatear a DD-MM-AAAA
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    
    return `${day}-${month}-${year}`;
  },

  /**
   * Formatea un valor de métrica según su schema
   * @param {*} value - Valor a formatear
   * @param {Object} metricSchema - Schema de la métrica
   * @returns {string} Valor formateado
   */
  formatMetric(value, metricSchema) {
    if (value === null || value === undefined) {
      return "0";
    }

    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
      return String(value);
    }

    if (!metricSchema) {
      return this.formatNumber(numValue);
    }

    const format = metricSchema.format || "";
    const dataType = metricSchema.data_type || "number";
    
    // Verificar también format_type directamente si está presente (para compatibilidad con builder)
    const formatType = metricSchema.format_type || "";

    // IMPORTANTE: Verificar integer PRIMERO antes de verificar format "number:"
    // porque cuando format_type es "integer", el formato es "number:0" pero debe tratarse como entero
    // Formato de entero (sin decimales) - debe verificarse ANTES de "number:"
    // Verificar: data_type === "integer", format === "number:0", o format_type === "integer"
    if (dataType === "integer" || format === "number:0" || formatType === "integer") {
      // Usar formatNumber con 0 decimales para consistencia con otros formatos
      return this.formatNumber(Math.round(numValue), 0);
    }

    // Formato de moneda con decimales configurables
    if (format.startsWith("currency") || dataType === "currency") {
      // Para ventas-netas, aplicar formateo en millones (solo visual)
      if (this.reportSlug === "ventas-netas") {
        return this.formatMillions(numValue);
      }
      
      // Si el formato es "currency:ARS:2" o similar, extraer decimales
      let decimals = 2; // Default para moneda
      if (format.includes(":")) {
        const parts = format.split(":");
        if (parts.length > 2) {
          // Formato: currency:ARS:2
          const decimalsPart = parseInt(parts[2]);
          if (!isNaN(decimalsPart)) {
            decimals = decimalsPart;
          }
        } else if (parts.length === 2) {
          // Formato: currency:2 (sin moneda especificada)
          const decimalsPart = parseInt(parts[1]);
          if (!isNaN(decimalsPart)) {
            decimals = decimalsPart;
          }
        }
      }
      // Debug: verificar que se esté formateando como moneda
      console.log("[formatMetric] Formateando como moneda:", {
        value: numValue,
        format: format,
        decimals: decimals,
        dataType: dataType
      });
      return this.formatCurrency(numValue, decimals);
    } 
    // Formato de porcentaje con decimales configurables
    else if (format.startsWith("percent:") || dataType === "percentage") {
      const decimals = format.includes(":") ? parseInt(format.split(":")[1]) : 2;
      return `${(numValue * 100).toFixed(decimals)}%`;
    } 
    // Formato de número con decimales configurables
    else if (format.startsWith("number:") || dataType === "number") {
      const decimals = format.includes(":") ? parseInt(format.split(":")[1]) : 2;
      return this.formatNumber(numValue, decimals);
    }

    // Default: número con 2 decimales
    return this.formatNumber(numValue, 2);
  },

  /**
   * Formatea un valor de dimensión según su schema
   * @param {*} value - Valor a formatear
   * @param {Object} dimensionSchema - Schema de la dimensión
   * @returns {string} Valor formateado
   */
  formatDimension(value, dimensionSchema) {
    if (value === null || value === undefined) {
      return "-";
    }

    if (!dimensionSchema) {
      return String(value);
    }

    const dataType = dimensionSchema.data_type || "string";
    const format = dimensionSchema.format || "";

    // Si es numérico y tiene formato configurado, usar formatMetric
    // También verificar si el valor es numérico aunque el data_type sea string
    const numValue = parseFloat(value);
    if (!isNaN(numValue) && (dataType === "integer" || dataType === "number" || format)) {
      // Crear un schema temporal para usar formatMetric
      // Si tiene formato, inferir data_type desde el formato
      let inferredDataType = dataType;
      if (format) {
        if (format.startsWith("currency")) {
          inferredDataType = "currency";
        } else if (format.startsWith("percent")) {
          inferredDataType = "percentage";
        } else if (format.startsWith("number:0") || format === "number:0") {
          inferredDataType = "integer";
        } else {
          inferredDataType = "number";
        }
      }
      const metricSchema = {
        data_type: inferredDataType,
        format: format
      };
      // Debug: verificar que el formato se esté pasando correctamente
      if (format && format.startsWith("currency")) {
        console.log("[formatDimension] Formateando como moneda:", {
          value: numValue,
          format: format,
          inferredDataType: inferredDataType
        });
      }
      return this.formatMetric(numValue, metricSchema);
    }

    if (dataType === "date" || dataType === "datetime") {
      // Usar formato DD-MM-AAAA
      return this.formatDateToDDMMYYYY(value);
    }

    return String(value);
  },

  /**
   * Formatea un número con separadores de miles
   * @param {number} value - Valor numérico
   * @param {number} decimals - Número de decimales
   * @returns {string} Número formateado
   */
  formatNumber(value, decimals = 2) {
    if (typeof value !== "number" || isNaN(value)) {
      return "0";
    }

    try {
      return new Intl.NumberFormat("es-AR", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      }).format(value);
    } catch (e) {
      return value.toFixed(decimals);
    }
  },

  /**
   * Formatea un valor como moneda
   * @param {number} value - Valor numérico
   * @param {number} decimals - Número de decimales (default: 2)
   * @returns {string} Valor formateado como moneda
   */
  formatCurrency(value, decimals = 2) {
    if (typeof value !== "number" || isNaN(value)) {
      return decimals === 0 ? "$0" : "$0," + "0".repeat(decimals);
    }

    try {
      // Formatear el número con separadores de miles y decimales
      const formatted = new Intl.NumberFormat("es-AR", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      }).format(value);
      
      // Agregar el símbolo $ al inicio
      return `$${formatted}`;
    } catch (e) {
      // Fallback: formateo manual con separadores correctos
      const parts = value.toFixed(decimals).split(".");
      const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
      const decimalPart = parts[1] || "0".repeat(decimals);
      return `$${integerPart},${decimalPart}`;
    }
  },

  /**
   * Formatea un valor en millones con sufijo "M"
   * - Siempre redondea a entero
   * - Si el resultado es >= 1000: muestra con separadores de miles (ej: "8.951M", "73.124M")
   * - Si el resultado es < 1000: muestra sin separadores (ej: "8M", "9M", "81M", "86M")
   * SOLO para visualización en gráficos (no modifica datos internos)
   * @param {number} value - Valor numérico a formatear
   * @returns {string} Valor formateado en millones
   */
  formatMillions(value) {
    if (typeof value !== "number" || isNaN(value)) {
      return "0M";
    }
    
    // Convertir a millones y redondear a entero
    const millions = value / 1000000;
    const rounded = Math.round(millions);
    
    // Si el resultado es >= 1000, mostrar con separadores de miles
    if (rounded >= 1000) {
      return rounded.toLocaleString("es-AR") + "M";
    }
    
    // Si es < 1000, mostrar sin separadores
    return rounded + "M";
  },

  /**
   * Formatea un valor de forma compacta (abreviada) para usar en etiquetas pequeñas
   * @param {number} value - Valor a formatear
   * @param {Object} metricSchema - Schema de la métrica
   * @returns {string} Valor formateado de forma compacta
   */
  formatMetricCompact(value, metricSchema) {
    if (value === null || value === undefined) {
      return "0";
    }

    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
      return String(value);
    }

    const absValue = Math.abs(numValue);
    const sign = numValue < 0 ? "-" : "";

    // Formato abreviado para valores grandes
    if (absValue >= 1000000000) {
      // Miles de millones
      const billions = (absValue / 1000000000).toFixed(1);
      return `${sign}$${billions.replace(".", ",")}M`;
    } else if (absValue >= 1000000) {
      // Millones
      const millions = (absValue / 1000000).toFixed(1);
      return `${sign}$${millions.replace(".", ",")}M`;
    } else if (absValue >= 1000) {
      // Miles
      const thousands = (absValue / 1000).toFixed(1);
      return `${sign}$${thousands.replace(".", ",")}K`;
    }

    // Para valores pequeños, usar formato normal pero más corto
    if (metricSchema && (metricSchema.data_type === "currency" || metricSchema.format?.startsWith("currency:"))) {
      return `${sign}$${absValue.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ".")}`;
    }

    return absValue.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }
};

// Exportar para uso global
if (typeof window !== "undefined") {
  window.WidgetEngine = WidgetEngine;
  console.log('[WidgetEngine] Exportado a window.WidgetEngine');
  
  // Disparar evento personalizado para notificar que WidgetEngine está listo
  if (typeof document !== "undefined") {
    // Usar setTimeout para asegurar que el evento se dispare después de que el DOM esté listo
    setTimeout(() => {
      document.dispatchEvent(new CustomEvent('widgetEngineReady', { detail: { WidgetEngine } }));
      console.log('[WidgetEngine] Evento widgetEngineReady disparado');
    }, 0);
  }
} else {
  console.warn('[WidgetEngine] window no está disponible, no se puede exportar');
}

