import { initializeTagsFilter } from "/static/reports/js/tags_filter.mjs";

function initTagsEstaticos() {
  document.querySelectorAll("select[data-tags-field]").forEach((sel) => {
    if (sel.dataset.synapTagsInit === "1") return;
    if (sel.id === "codigos_incluidos") return;
    sel.dataset.synapTagsInit = "1";
    const fieldId = sel.getAttribute("data-tags-field") || sel.id;
    if (fieldId) initializeTagsFilter(fieldId);
  });
}

function initCodigosPredictivo() {
  const cfg = document.getElementById("precios-terminados-config");
  if (!cfg) return;
  const apiUrl = cfg.dataset.apiArticulos || "";
  const tipoProducto = cfg.dataset.tipoProducto || "terminado";
  const sel = document.getElementById("codigos_incluidos");
  if (!sel || sel.dataset.synapTagsInit === "1") return;
  sel.dataset.synapTagsInit = "1";

  initializeTagsFilter("codigos_incluidos", "articulos", null, {
    remoteSearch: {
      minChars: 2,
      fetchFn: async (q) => {
        const excluir = Array.from(sel.selectedOptions)
          .map((o) => o.value)
          .filter(Boolean)
          .join(",");
        const params = new URLSearchParams({
          q,
          tipo_producto: tipoProducto,
        });
        if (excluir) params.set("excluir", excluir);
        const r = await fetch(`${apiUrl}?${params}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!r.ok) return [];
        const data = await r.json();
        return (data.articulos || []).map((a) => ({
          value: String(a.id_articulo),
          label: a.codigo_display || `${a.id_manual} — ${a.nombre}`,
        }));
      },
    },
  });
}

function boot() {
  initTagsEstaticos();
  initCodigosPredictivo();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
