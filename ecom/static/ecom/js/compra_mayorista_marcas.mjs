/**
 * Filtro multi-marca (tags_filter) — pedido de venta.
 * Carga marcas ecommerce y notifica a Alpine para recargar la búsqueda.
 */
import { initializeTagsFilter } from "/static/reports/js/tags_filter.mjs";

const FIELD_ID = "compra_marcas_incluidos";

async function cargarOpcionesMarcas(url, select) {
  const r = await fetch(`${url}?ajax=1`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!r.ok) return;
  let data = null;
  try {
    data = await r.json();
  } catch {
    return;
  }
  const marcas = Array.isArray(data) ? data : [];
  marcas.forEach((m) => {
    if (m == null || m.id == null) return;
    const opt = document.createElement("option");
    opt.value = String(m.id);
    opt.textContent = m.name || String(m.id);
    select.appendChild(opt);
  });
}

function notificarCambio(select) {
  const marcas = Array.from(select.selectedOptions)
    .map((o) => o.value)
    .filter(Boolean);
  window.dispatchEvent(
    new CustomEvent("compra-marcas-cambiadas", { detail: { marcas } }),
  );
}

async function init() {
  const panel = document.getElementById("compra-marcas-panel");
  if (!panel) return;
  const url = panel.getAttribute("data-marcas-url");
  const select = document.getElementById(FIELD_ID);
  if (!url || !select || select.dataset.synapTagsInit === "1") return;

  await cargarOpcionesMarcas(url, select);
  initializeTagsFilter(FIELD_ID, "marcas");
  select.dataset.synapTagsInit = "1";
  select.addEventListener("change", () => notificarCambio(select));
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
