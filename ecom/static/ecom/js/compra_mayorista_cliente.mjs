/**
 * Búsqueda predictiva de cliente — compra mayorista (dropdown único, Synap).
 * El cliente NO se restaura desde sesión: cada carga de pantalla inicia vacío.
 */
import { wireCompraClientePredictiveFromRoot } from "./ecom_predictive.mjs";

function init() {
  const root = document.getElementById("compra-cliente-panel");
  if (!root) return;
  const api = wireCompraClientePredictiveFromRoot(root);
  if (!api) return;

  window.addEventListener("compra-cliente-limpiado", () => {
    api.setDisplay("");
  });
  window.addEventListener("compra-cliente-display", (e) => {
    const label = e.detail && e.detail.label;
    if (label) api.setDisplay(String(label));
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
