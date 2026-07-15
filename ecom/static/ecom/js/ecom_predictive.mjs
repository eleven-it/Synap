/**
 * Búsqueda predictiva Synap para el módulo ecom.
 * Desplegable con debounce, navegación por teclado y cierre al hacer clic fuera.
 */

const DEFAULT_DEBOUNCE_MS = 280;

function esc(text) {
  const d = document.createElement("div");
  d.textContent = text == null ? "" : String(text);
  return d.innerHTML;
}

function normalizeItem(item) {
  if (item == null) return { value: "", label: "" };
  if (typeof item === "string") return { value: item, label: item };
  return {
    value: String(item.value ?? item.label ?? ""),
    label: String(item.label ?? item.value ?? ""),
  };
}

/**
 * @param {object} opts
 * @param {HTMLInputElement} opts.input
 * @param {HTMLElement} opts.dropdown
 * @param {number} [opts.minChars=2]
 * @param {number} [opts.debounceMs=280]
 * @param {(query: string) => Promise<Array<string|{value: string, label: string}>>} opts.fetchItems
 * @param {(query: string) => Promise<Array<string|{value: string, label: string}>>} [opts.fetchItemsExpanded]
 * @param {(item: {value: string, label: string}) => void} [opts.onPick]
 * @param {string} [opts.emptyMessage]
 * @param {HTMLElement} [opts.boundary] — contenedor para cerrar al clic fuera
 * @returns {{ destroy: () => void, setDisplay: (label: string) => void }}
 */
export function initPredictiveInput(opts) {
  const input = opts.input;
  const dropdown = opts.dropdown;
  if (!input || !dropdown) {
    return { destroy() {}, setDisplay() {} };
  }

  const minChars = opts.minChars ?? 2;
  const debounceMs = opts.debounceMs ?? DEFAULT_DEBOUNCE_MS;
  const emptyMessage = opts.emptyMessage || "Sin resultados";
  const boundary = opts.boundary || input.closest(".relative") || input.parentElement;

  let timer = null;
  let highlight = -1;
  let lastItems = [];
  let expandedOnce = false;

  dropdown.setAttribute("role", "listbox");
  input.setAttribute("aria-expanded", "false");
  if (!input.getAttribute("aria-haspopup")) {
    input.setAttribute("aria-haspopup", "listbox");
  }

  function syncComboboxAria(open) {
    input.setAttribute("aria-expanded", open ? "true" : "false");
    if (!open) {
      input.removeAttribute("aria-activedescendant");
    } else if (highlight >= 0) {
      input.setAttribute("aria-activedescendant", `predictive-option-${highlight}`);
    }
  }

  function hide() {
    dropdown.classList.add("hidden");
    highlight = -1;
    syncComboboxAria(false);
  }

  function show() {
    dropdown.classList.remove("hidden");
    syncComboboxAria(true);
  }

  function render(items, query) {
    dropdown.innerHTML = "";
    lastItems = items || [];

    if (!lastItems.length) {
      const empty = document.createElement("div");
      empty.className = "px-3 py-2 text-xs text-slate-500 dark:text-slate-400";
      empty.textContent = query.length >= minChars ? emptyMessage : `Escriba al menos ${minChars} caracteres…`;
      dropdown.appendChild(empty);
      show();
      return;
    }

    lastItems.forEach((raw, index) => {
      const item = normalizeItem(raw);
      const row = document.createElement("button");
      row.type = "button";
      row.id = `predictive-option-${index}`;
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", index === highlight ? "true" : "false");
      row.className =
        "w-full text-left px-3 py-2 text-xs transition-colors min-h-[2.75rem] " +
        (index === highlight
          ? "bg-sky-100 dark:bg-sky-900 text-sky-800 dark:text-sky-200"
          : "text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700");
      row.innerHTML = esc(item.label);
      row.addEventListener("mousedown", (e) => e.preventDefault());
      row.addEventListener("click", () => pick(item));
      dropdown.appendChild(row);
    });
    show();
    if (highlight >= 0) {
      input.setAttribute("aria-activedescendant", `predictive-option-${highlight}`);
    }
  }

  function pick(item) {
    const n = normalizeItem(item);
    input.value = n.label;
    hide();
    if (typeof opts.onPick === "function") opts.onPick(n);
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function runSearch(query, expanded) {
    try {
      const fetchFn =
        expanded && typeof opts.fetchItemsExpanded === "function"
          ? opts.fetchItemsExpanded
          : opts.fetchItems;
      const items = await fetchFn(query);
      if (expanded) expandedOnce = true;
      render(Array.isArray(items) ? items : [], query);
    } catch {
      render([], query);
    }
  }

  function schedule(query) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      runSearch(query, false);
    }, debounceMs);
  }

  function onInput() {
    const q = input.value.trim();
    highlight = -1;
    expandedOnce = false;
    if (q.length < minChars) {
      render([], q);
      return;
    }
    schedule(q);
  }

  async function expandOnArrowDown(q) {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    const useExpanded = typeof opts.fetchItemsExpanded === "function" && !expandedOnce;
    await runSearch(q, useExpanded);
    if (lastItems.length) {
      highlight = 0;
      render(lastItems, q);
    }
  }

  function onKeydown(e) {
    const q = input.value.trim();
    if (e.key === "ArrowDown" && q.length >= minChars) {
      if (dropdown.classList.contains("hidden") || highlight < 0) {
        e.preventDefault();
        expandOnArrowDown(q);
        return;
      }
    }
    if (dropdown.classList.contains("hidden") && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      onInput();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!lastItems.length) return;
      highlight = Math.min(highlight + 1, lastItems.length - 1);
      render(lastItems, input.value.trim());
      const rows = dropdown.querySelectorAll("button");
      rows[highlight]?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!lastItems.length) return;
      highlight = Math.max(highlight - 1, 0);
      render(lastItems, input.value.trim());
      const rows = dropdown.querySelectorAll("button");
      rows[highlight]?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter" && highlight >= 0 && lastItems[highlight]) {
      e.preventDefault();
      pick(lastItems[highlight]);
    } else if (e.key === "Escape") {
      hide();
      input.focus();
    }
  }

  input.addEventListener("input", onInput);
  input.addEventListener("focus", onInput);
  input.addEventListener("keydown", onKeydown);

  const onDocClick = (e) => {
    if (!boundary?.contains(e.target)) hide();
  };
  document.addEventListener("click", onDocClick);

  return {
    destroy() {
      if (timer) clearTimeout(timer);
      input.removeEventListener("input", onInput);
      input.removeEventListener("focus", onInput);
      input.removeEventListener("keydown", onKeydown);
      document.removeEventListener("click", onDocClick);
    },
    setDisplay(label) {
      input.value = label == null ? "" : String(label);
    },
  };
}

/**
 * Sugerencias de número de comprobante (relays `sugerencias-nro` o v1).
 * @param {string} apiUrl — URL base con query fija (ajax, tipo, etc.)
 * @param {string} [resultsKey] — clave JSON (`sugerencias` legacy o `results` v1)
 */
export function fetchSugerenciasComprobante(apiUrl, resultsKey) {
  return async function (query) {
    const sep = apiUrl.includes("?") ? "&" : "?";
    const r = await fetch(`${apiUrl}${sep}q=${encodeURIComponent(query)}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();
    if (resultsKey && Array.isArray(data[resultsKey])) return data[resultsKey];
    if (Array.isArray(data.results)) return data.results;
    if (Array.isArray(data.sugerencias)) return data.sugerencias;
    return [];
  };
}

/**
 * Conecta búsqueda predictiva al campo `#numeroComp` si el contenedor expone `data-sugerencias-url`.
 */
export function wireNumeroCompPredictiveFromRoot(root) {
  if (!root) return;
  const apiUrl = root.getAttribute("data-sugerencias-url");
  if (!apiUrl) return;
  const input = document.getElementById("numeroComp");
  const dropdown = document.getElementById("numeroComp_dropdown");
  if (!input || !dropdown || input.dataset.ecomPredictiveInit === "1") return;
  input.dataset.ecomPredictiveInit = "1";
  const resultsKey = root.getAttribute("data-sugerencias-key") || "";
  initPredictiveInput({
    input,
    dropdown,
    minChars: 2,
    fetchItems: fetchSugerenciasComprobante(apiUrl, resultsKey),
  });
}

export function autoInitNumeroCompPredictive() {
  document
    .querySelectorAll("[data-sugerencias-url]")
    .forEach(wireNumeroCompPredictiveFromRoot);
}

/**
 * Búsqueda predictiva de clientes mayoristapp (selección única, dropdown).
 */
export function fetchClientesMayoristapp(buscarUrl, limit) {
  const lim = limit != null ? String(limit) : "15";
  return async function (query) {
    const params = new URLSearchParams({
      ajax: "1",
      modoBus: "texto",
      patron: query,
      q: query,
      limit: lim,
    });
    const r = await fetch(`${buscarUrl}?${params}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();
    const rows = data.results || data.clientes || [];
    return rows.map((c) => {
      const cod = c.id != null ? c.id : c.Codigo != null ? c.Codigo : c.codigo;
      const nombre = (c.text || c.nombre_cliente || c.nombre || "").trim();
      const label = nombre ? `${nombre} (#${cod})` : String(cod);
      return { value: String(cod), label };
    });
  };
}

/**
 * Conecta búsqueda predictiva de cliente en compra mayorista (`#compra-cliente-panel`).
 */
export function wireCompraClientePredictiveFromRoot(root) {
  if (!root) return null;
  const buscarUrl = root.getAttribute("data-buscar-url");
  const seleccionarUrl = root.getAttribute("data-seleccionar-url");
  if (!buscarUrl || !seleccionarUrl) return null;

  const input = document.getElementById("compra_cliente_search");
  const dropdown = document.getElementById("compra_cliente_dropdown");
  if (!input || !dropdown || input.dataset.ecomPredictiveInit === "1") return null;
  input.dataset.ecomPredictiveInit = "1";

  let picking = false;

  function getCsrf() {
    const m = document.cookie.match("(^|;)\\s*csrftoken\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }

  const api = initPredictiveInput({
    input,
    dropdown,
    minChars: 2,
    emptyMessage: "No se encontraron clientes",
    fetchItems: fetchClientesMayoristapp(buscarUrl, 15),
    fetchItemsExpanded: fetchClientesMayoristapp(buscarUrl, 50),
    onPick(item) {
      if (picking || !item.value) return;
      picking = true;
      root.dispatchEvent(
        new CustomEvent("compra-cliente-pick", {
          detail: { cod: item.value, label: item.label },
          bubbles: true,
        }),
      );
      fetch(`${seleccionarUrl}?ajax=1`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": getCsrf(),
        },
        body: JSON.stringify({ codigo: item.value, Codigo: item.value }),
      })
        .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
        .then(({ ok, data }) => {
          picking = false;
          if (ok) {
            window.dispatchEvent(
              new CustomEvent("compra-cliente-seleccionado", {
                detail: {
                  cod: item.value,
                  label: item.label,
                  fromSession: false,
                  listaPrecio: data && data.listaPrecio,
                  lista_precio_pdf_url: data && data.lista_precio_pdf_url,
                },
              }),
            );
          } else {
            api.setDisplay("");
            window.dispatchEvent(
              new CustomEvent("compra-cliente-error", {
                detail: { message: "No se pudo seleccionar el cliente." },
              }),
            );
          }
        })
        .catch(() => {
          picking = false;
          api.setDisplay("");
          window.dispatchEvent(
            new CustomEvent("compra-cliente-error", {
              detail: { message: "No se pudo seleccionar el cliente." },
            }),
          );
        });
    },
  });

  return api;
}
