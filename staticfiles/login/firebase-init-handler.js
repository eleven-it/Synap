import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import {
  getAuth,
  getRedirectResult,
  browserSessionPersistence
} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";

import { firebaseConfig, backendRoutes, getCookie } from "/login/firebase-config.js";

console.log("🔁 Ejecutando firebase-init-handler.js...");
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
auth.useDeviceLanguage();

auth.setPersistence(browserSessionPersistence)
  .then(() => {
    console.log("🔒 Persistence configurada");
    return getRedirectResult(auth);
  })
  .then((result) => {
    console.log("🔍 Resultado del redirect:", result);

    if (result && result.user) {
      return result.user.getIdToken().then((idToken) => {
        console.log("➡️ Enviando ID token al backend...");
        return fetch(backendRoutes.login, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
          },
          credentials: "same-origin",
          body: JSON.stringify({ idToken })
        });
      });
    } else {
      console.warn("⚠️ No se recibió ningún usuario desde el redirect.");
    }
  })
  .then((response) => {
    if (response && response.ok) {
      console.log("✅ Redirigiendo al dashboard...");
      window.location.href = "/dashboard/";
    }
  })
  .catch((error) => {
    console.error("❌ Error en redirect login:", error);
    showError("Error al procesar login: " + error.message);
  });

function showError(message) {
  alert(message);
}
