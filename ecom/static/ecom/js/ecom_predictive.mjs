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

/**
 * @param {object} opts
 * @param {HTMLInputElement} opts.input
 * @param {HTMLElement} opts.dropdown
 * @param {number} [opts.minChars=2]
 * @param {number} [opts.debounceMs=280]
 * @param {(query: string) => Promise<string[]>} opts.fetchItems
 * @param {(value: string) => void} [opts.onPick]
 * @param {string} [opts.emptyMessage]
 * @param {HTMLElement} [opts.boundary] — contenedor para cerrar al clic fuera
 */
export function initPredictiveInput(opts) {
  const input = opts.input;
  const dropdown = opts.dropdown;
  if (!input || !dropdown) return () => {};

  const minChars = opts.minChars ?? 2;
  const debounceMs = opts.debounceMs ?? DEFAULT_DEBOUNCE_MS;
  const emptyMessage = opts.emptyMessage || "Sin resultados";
  const boundary = opts.boundary || input.closest(".relative") || input.parentElement;

  let timer = null;
  let highlight = -1;
  let lastItems = [];

  function hide() {
    dropdown.classList.add("hidden");
    highlight = -1;
  }

  function show() {
    dropdown.classList.remove("hidden");
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

    lastItems.forEach((label, index) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className =
        "w-full text-left px-3 py-2 text-xs transition-colors " +
        (index === highlight
          ? "bg-sky-100 dark:bg-sky-900 text-sky-800 dark:text-sky-200"
          : "text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700");
      row.innerHTML = esc(label);
      row.addEventListener("mousedown", (e) => e.preventDefault());
      row.addEventListener("click", () => pick(label));
      dropdown.appendChild(row);
    });
    show();
  }

  function pick(value) {
    input.value = value;
    hide();
    if (typeof opts.onPick === "function") opts.onPick(value);
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function runSearch(query) {
    try {
      const items = await opts.fetchItems(query);
      render(Array.isArray(items) ? items : [], query);
    } catch {
      render([], query);
    }
  }

  function schedule(query) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      runSearch(query);
    }, debounceMs);
  }

  function onInput() {
    const q = input.value.trim();
    highlight = -1;
    if (q.length < minChars) {
      render([], q);
      return;
    }
    schedule(q);
  }

  function onKeydown(e) {
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
      input.blur();
    }
  }

  input.addEventListener("input", onInput);
  input.addEventListener("focus", onInput);
  input.addEventListener("keydown", onKeydown);

  const onDocClick = (e) => {
    if (!boundary?.contains(e.target)) hide();
  };
  document.addEventListener("click", onDocClick);

  return () => {
    if (timer) clearTimeout(timer);
    input.removeEventListener("input", onInput);
    input.removeEventListener("focus", onInput);
    input.removeEventListener("keydown", onKeydown);
    document.removeEventListener("click", onDocClick);
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
