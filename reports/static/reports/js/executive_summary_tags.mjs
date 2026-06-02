/**
 * Carga tags_filter.mjs antes que executive_summary.js (defer) y expone el inicializador.
 */
import { initializeTagsFilter } from "./tags_filter.mjs";

window.initializeTagsFilter = initializeTagsFilter;
window.execInitSucursalesTags = () =>
  initializeTagsFilter("exec_sucursales", "sucursales");
