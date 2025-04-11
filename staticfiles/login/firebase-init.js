import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithRedirect,
  GoogleAuthProvider,
  OAuthProvider
} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";

import {
  getFirestore,
  doc,
  setDoc,
  getDoc
} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-firestore.js";

import { firebaseConfig, backendRoutes, getCookie } from "/login/firebase-config.js";

console.log("✅ Firebase config cargado:", firebaseConfig);

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
auth.useDeviceLanguage();

console.log("✅ Firebase App inicializado");

const db = getFirestore();

// 🔐 Login con email y contraseña
window.loginUser = (event) => {
  event.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  document.getElementById("error-message").classList.add("hidden");

  signInWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      return userCredential.user.getIdToken().then((idToken) => {
        return fetch(backendRoutes.login, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
          },
          credentials: "same-origin",
          body: JSON.stringify({ idToken })
        }).then(() => {
          return verificarTipoUsuarioYRedirigir(userCredential.user);
        });
      });
    })
    .catch((error) => {
      showError(
        error.code === "auth/invalid-credential"
          ? "Correo o contraseña incorrectos."
          : "Error: " + error.message
      );
    });
};


// 🆕 Registro con email y contraseña con trazas
window.registerUser = function (event) {
  event.preventDefault();

  const nombre = document.getElementById("nombre").value;
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const errorBox = document.getElementById("error-message");

  errorBox.classList.add("hidden");

  console.log("📝 Iniciando registro...");
  console.log("📨 Email:", email);
  console.log("🔐 Password (oculto)");
  console.log("👤 Nombre:", nombre);

  createUserWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      const user = userCredential.user;
      console.log("✅ Usuario creado con UID:", user.uid);
      console.log("🧠 Guardando nombre en localStorage:", nombre);
      localStorage.setItem("nombre", nombre);

      console.log("➡️ Redirigiendo a completar perfil...");
      window.location.href = "/login/completar-perfil/";
    })
    .catch((error) => {
      console.error("❌ Error al registrar usuario:", error);
      errorBox.innerText = "Error: " + error.message;
      errorBox.classList.remove("hidden");
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

// 🔍 Verificar tipo_usuario después del login
async function verificarTipoUsuarioYRedirigir(user) {
  const usuarioRef = doc(db, "usuarios", user.uid);
  const docSnap = await getDoc(usuarioRef);

  if (!docSnap.exists() || !docSnap.data().tipo_usuario) {
    console.log("👤 Usuario sin tipo asignado. Redirigiendo a completar perfil.");
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

// 🔁 Guardar tipo de usuario en Firestore y redirigir
window.guardarTipoUsuario = async function (tipo) {
  const errorBox = document.getElementById("error-message");
  const authInstance = getAuth();

  console.log("🧭 Tipo seleccionado:", tipo);

  const unsubscribe = authInstance.onAuthStateChanged(async (user) => {
    unsubscribe(); // Dejamos de escuchar

    console.log("👤 Usuario actual:", user);

    if (!user) {
      errorBox.innerText = "No se detectó sesión activa.";
      errorBox.classList.remove("hidden");
      return;
    }

    try {
      // 1. Guardar tipo en Firestore
      await setDoc(doc(db, "usuarios", user.uid), {
        email: user.email,
        tipo_usuario: tipo,
        nombre: localStorage.getItem("nombre") || ""
      }, { merge: true });

      console.log("✅ Tipo de usuario guardado:", tipo);

      // 2. Obtener el token y enviarlo al backend
      const idToken = await user.getIdToken();
      const csrftoken = getCookie("csrftoken");

      const response = await fetch(backendRoutes.login, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken
        },
        credentials: "same-origin",
        body: JSON.stringify({ idToken })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("❌ Error al enviar token al backend:", errorText);
        throw new Error("No se pudo establecer sesión con el backend.");
      }

      console.log("✅ Sesión establecida con backend");

      // 3. Redirigir según tipo
      if (tipo === "cliente") {
        console.log("➡️ Redirigiendo a /clientes/dashboard/");
        window.location.href = "/clientes/dashboard/";
      } else {
        console.log("➡️ Redirigiendo a /proveedores/dashboard/");
        window.location.href = "/proveedores/dashboard/";
      }

    } catch (error) {
      console.error("❌ Error en guardarTipoUsuario:", error);
      errorBox.innerText = "Error al guardar el tipo de cuenta. Intentá nuevamente.";
      errorBox.classList.remove("hidden");
    }
  });
};


// window.guardarTipoUsuario = async function (tipo) {
//   const errorBox = document.getElementById("error-message");

//   const authInstance = getAuth();
//   const unsubscribe = authInstance.onAuthStateChanged(async (user) => {
//     unsubscribe(); // dejar de escuchar

//     console.log("👤 Usuario actual:", user);

//     if (!user) {
//       errorBox.innerText = "No se detectó sesión activa.";
//       errorBox.classList.remove("hidden");
//       return;
//     }

//     try {
//       // 1. Guardar en Firestore    
//       await setDoc(doc(db, "usuarios", user.uid), {
//         email: user.email,
//         tipo_usuario: tipo,
//         nombre: localStorage.getItem("nombre") || ""
//       }, { merge: true });

//       console.log("✅ Tipo de usuario guardado:", tipo);

//       // 2. Obtener el token y enviarlo al backend    
//       const idToken = await user.getIdToken();
//       const csrftoken = getCookie("csrftoken");

//       const response = await fetch(backendRoutes.login, {
//         method: "POST",
//         headers: {
//           "Content-Type": "application/json",
//           "X-CSRFToken": csrftoken
//         },
//         credentials: "same-origin",
//         body: JSON.stringify({ idToken })
//       });

//       if (!response.ok) {
//         throw new Error("No se pudo establecer la sesión con el backend.");
//       }

//       // 3. Redirigir al dashboard según tipo    
//       if (tipo === "cliente") {
//         window.location.href = "/clientes/dashboard/";
//       } else {
//         window.location.href = "/proveedores/dashboard/";
//       }
//     } catch (error) {
//       console.error("❌ Error al guardar tipo de usuario:", error);
//       errorBox.innerText = "Error al guardar el tipo de cuenta. Intentá nuevamente.";
//       errorBox.classList.remove("hidden");
//     }
//   });
// };

