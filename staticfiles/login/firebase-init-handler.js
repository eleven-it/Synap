import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import {
  getAuth,
  getRedirectResult,
  browserSessionPersistence
} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";
import { firebaseConfig, backendRoutes, getCookie } from "/login/firebase-config.js";

// 🔧 Inicialización
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
auth.useDeviceLanguage();

// 🔍 Obtener el parámetro `next` de la URL
function getNextParam() {
  const params = new URLSearchParams(window.location.search);
  return params.get("next");
}

// 🔐 Persistencia y manejo del login por redirect
auth.setPersistence(browserSessionPersistence)
  .then(() => getRedirectResult(auth))
  .then((result) => {
    if (result && result.user) {
      return result.user.getIdToken().then((idToken) => {
        return fetch(backendRoutes.login, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
          },
          credentials: "same-origin",
          body: JSON.stringify({ idToken })
        }).then(response => {
          if (!response.ok) throw new Error("Error al iniciar sesión.");
          return response.json();
        }).then((data) => {
          const nextParam = getNextParam();
          const redirectUrl = nextParam || data.redirect || "/core/dashboard/";
          window.location.href = redirectUrl;
        });
      });
    } else {
      console.warn("⚠️ No se recibió usuario en el redirect.");
    }
  })
  .catch((error) => {
    alert("Error al iniciar sesión: " + error.message);
  });
