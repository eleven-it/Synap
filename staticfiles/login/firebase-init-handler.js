import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import {
  getAuth,
  getRedirectResult,
  browserSessionPersistence
} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";
import {
  getFirestore,
  doc,
  getDoc
} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-firestore.js";
import { firebaseConfig, backendRoutes, getCookie } from "/login/firebase-config.js";

console.log("🔁 Ejecutando firebase-init-handler.js...");
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
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
        }).then(() => {
          return verificarTipoUsuarioYRedirigir(result.user);
        });
      });
    } else {
      console.warn("⚠️ No se recibió ningún usuario desde el redirect.");
    }
  })
  .catch((error) => {
    console.error("❌ Error en redirect login:", error);
    showError("Error al procesar login: " + error.message);
  });

function showError(message) {
  alert(message);
}

// 🔍 Verificar tipo_usuario y redirigir según corresponda
async function verificarTipoUsuarioYRedirigir(user) {
  const usuarioRef = doc(db, "usuarios", user.uid);
  const docSnap = await getDoc(usuarioRef);

  if (!docSnap.exists() || !docSnap.data().tipo_usuario) {
    console.log("👤 Usuario sin tipo. Redirigiendo a completar perfil.");
    window.location.href = "/login/completar-perfil/";
    return;
  }

  const tipo = docSnap.data().tipo_usuario;
  console.log("✅ Tipo de usuario:", tipo);

  if (tipo === "cliente") {
    window.location.href = "/clientes/dashboard/";
  } else {
    window.location.href = "/proveedores/dashboard/";
  }
}
