import { firebaseConfig, backendRoutes } from "/login/firebase-config.js";
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  updateProfile,
  signInWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  OAuthProvider
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

function getNextParam() {
  const params = new URLSearchParams(window.location.search);
  return params.get("next") || "/core/dashboard/";
}

async function sendLoginRequest(idToken) {
  const next = getNextParam();

  const response = await fetch(`/login/?next=${encodeURIComponent(next)}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ idToken }),
  });

  const data = await response.json();

  if (response.ok && data.redirect) {
    window.location.href = data.redirect;
  } else {
    const errorDiv = document.getElementById("error-message");
    if (errorDiv) {
      errorDiv.innerText = data.error || "Error desconocido";
      errorDiv.classList.remove("hidden");
    }
  }
}

// 🔐 Login por email
window.loginUser = async function (event) {
  event.preventDefault();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const errorDiv = document.getElementById("error-message");

  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const idToken = await userCredential.user.getIdToken();
    await sendLoginRequest(idToken);
  } catch (error) {
    if (errorDiv) {
      errorDiv.innerText = "Credenciales inválidas";
      errorDiv.classList.remove("hidden");
    }
  }
};

// 🔐 Login con Google
window.loginWithGoogle = async function () {
  const provider = new GoogleAuthProvider();
  try {
    const result = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken();
    await sendLoginRequest(idToken);
  } catch (error) {
    console.error("Login con Google falló:", error);
  }
};

// 🔐 Login con Apple (placeholder)
window.loginWithApple = async function () {
  const provider = new OAuthProvider("apple.com");
  try {
    const result = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken();
    await sendLoginRequest(idToken);
  } catch (error) {
    console.error("Login con Apple falló:", error);
  }
};

// ➕ Función de Registro que faltaba
window.registerUser = async function (event) {
  event.preventDefault();
  const nombre = document.getElementById("nombre").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const errorDiv = document.getElementById("error-message");

  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    
    // Actualizar el perfil del usuario con el nombre
    await updateProfile(userCredential.user, {
      displayName: nombre
    });

    const idToken = await userCredential.user.getIdToken();
    await sendLoginRequest(idToken); // Reutilizamos el flujo de login

  } catch (error) {
    if (errorDiv) {
      errorDiv.innerText = error.message; // Mostrar error de Firebase
      errorDiv.classList.remove("hidden");
    }
  }
};
