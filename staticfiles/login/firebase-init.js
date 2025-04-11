import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import {
  getAuth,
  signInWithEmailAndPassword,
  signInWithRedirect,
  GoogleAuthProvider,
  OAuthProvider
} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";

import { firebaseConfig, backendRoutes, getCookie } from "/login/firebase-config.js";

console.log("✅ Firebase config cargado:", firebaseConfig);

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
auth.useDeviceLanguage();

console.log("✅ Firebase App inicializado");

// 🔐 Login con email y contraseña
window.loginUser = (event) => {
  event.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  document.getElementById("error-message").classList.add("hidden");

  signInWithEmailAndPassword(auth, email, password)
    .then((userCredential) => userCredential.user.getIdToken())
    .then((idToken) => sendTokenToBackend(idToken))
    .catch((error) => {
      showError(
        error.code === "auth/invalid-credential"
          ? "Correo o contraseña incorrectos."
          : "Error: " + error.message
      );
    });
};

// 🚀 Google login con redirect
window.loginWithGoogle = () => {
  console.log("🔁 Redireccionando a login con Google...");
  signInWithRedirect(auth, new GoogleAuthProvider());
};

// 🍏 Apple login con redirect
window.loginWithApple = () => {
  console.log("🔁 Redireccionando a login con Apple...");
  signInWithRedirect(auth, new OAuthProvider("apple.com"));
};

const sendTokenToBackend = (idToken) => {
  const csrftoken = getCookie("csrftoken");
  fetch(backendRoutes.login, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrftoken
    },
    credentials: "same-origin",
    body: JSON.stringify({ idToken })
  })
    .then((response) => {
      if (response.ok) {
        window.location.href = "/dashboard/";
      } else {
        throw new Error("Error al validar el token.");
      }
    })
    .catch((error) => {
      showError(error.message);
    });
};

const showError = (message) => {
  const msg = document.getElementById("error-message");
  if (msg) {
    msg.innerText = message;
    msg.classList.remove("hidden");
  } else {
    alert(message);
  }
};
