import { autoInitNumeroCompPredictive } from "./ecom_predictive.mjs";

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", autoInitNumeroCompPredictive);
} else {
  autoInitNumeroCompPredictive();
}
