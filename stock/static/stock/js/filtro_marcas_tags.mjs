import { initializeTagsFilter } from "/static/reports/js/tags_filter.mjs";

function initMarcasTags() {
  document.querySelectorAll("select[data-tags-field]").forEach((sel) => {
    if (sel.dataset.synapTagsInit === "1") {
      return;
    }
    sel.dataset.synapTagsInit = "1";
    const fieldId = sel.getAttribute("data-tags-field") || sel.id;
    if (fieldId) {
      initializeTagsFilter(fieldId, "marcas");
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMarcasTags);
} else {
  initMarcasTags();
}
