import { initializeTagsFilter } from "/static/reports/js/tags_filter.mjs";

document.addEventListener("DOMContentLoaded", () => {
  const sel = document.getElementById("marcas_incluidos");
  if (sel) {
    initializeTagsFilter("marcas_incluidos", "marcas");
  }
});
