const workspaceSection = document.querySelector("section[data-workspace-api]");
const workspaceApiUrl = workspaceSection ? workspaceSection.dataset.workspaceApi : null;

const getCsrfToken = () => {
  const name = "csrftoken";
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (let i = 0; i < cookies.length; i += 1) {
    const cookie = cookies[i].trim();
    if (cookie.startsWith(`${name}=`)) {
      return decodeURIComponent(cookie.substring(name.length + 1));
    }
  }
  return "";
};

const showToast = (message, type = "success") => {
  const container = document.createElement("div");
  container.className = `fixed top-5 right-5 z-50 px-4 py-3 rounded-xl shadow-2xl text-xs font-semibold tracking-wide ${
    type === "success" ? "bg-emerald-500 text-white" : "bg-rose-500 text-white"
  } animate-[fade-in_0.4s_ease-out]`;
  container.innerText = message;
  document.body.appendChild(container);
  setTimeout(() => {
    container.classList.add("animate-[fade-out_0.3s_ease-in_forwards]");
    container.addEventListener("animationend", () => container.remove());
  }, 2500);
};

const updateWorkspaceCount = (count) => {
  const countNode = document.querySelector("[data-workspace-count]");
  if (countNode) {
    countNode.textContent = count;
  }
};

const markButtonSaved = (button, isListStyle = false) => {
  button.dataset.saved = "true";
  button.classList.remove("text-sky-500", "hover:text-sky-400", "opacity-60", "pointer-events-none");
  button.classList.remove("hover:bg-sky-50", "dark:hover:bg-sky-900/20");
  button.classList.add("text-emerald-500", "opacity-100");
  button.classList.add("pointer-events-none", "cursor-default");
  button.dataset.loading = "false";
  button.innerHTML = `
    <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path d="M5 13l4 4L19 7" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    Guardado
  `;
};

const markButtonInWorkspace = (button) => {
  button.dataset.inWorkspace = "true";
  button.classList.remove("text-sky-500", "hover:text-sky-400");
  button.classList.add("text-emerald-500", "hover:text-emerald-400");
  button.dataset.loading = "false";
  button.innerHTML = `
    <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path d="M5 5v14l7-4 7 4V5a2 2 0 00-2-2H7a2 2 0 00-2 2z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    En workspace
  `;
};

const resetButtonToGuardar = (button, isListStyle = false) => {
  button.dataset.saved = "false";
  button.dataset.inWorkspace = "false";
  button.classList.remove("text-emerald-500", "hover:text-emerald-400", "pointer-events-none", "cursor-default");
  button.classList.add("text-sky-500", "hover:text-sky-400");
  if (button.closest("table")) {
    button.classList.add("hover:bg-sky-50", "dark:hover:bg-sky-900/20");
  }
  button.dataset.loading = "false";
  button.innerHTML = `
    <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path d="M5 5v14l7-4 7 4V5a2 2 0 00-2-2H7a2 2 0 00-2 2z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    ${isListStyle ? "Guardar" : "Guardar en workspace"}
  `;
};

const syncWorkspaceState = async () => {
  if (!workspaceApiUrl) {
    return;
  }
  try {
    const response = await fetch(workspaceApiUrl, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    if (!response.ok) {
      throw new Error("No se pudo cargar el estado del workspace");
    }
    const payload = await response.json();
    const slots = payload.slots || [];
    const slugsInWorkspace = new Set(slots.map((s) => s.slug));
    updateWorkspaceCount(payload.count ?? slots.length);

    const buttons = document.querySelectorAll("[data-add-to-workspace]");
    buttons.forEach((button) => {
      const slug = button.dataset.reportSlug;
      if (!slug) return;
      const allowDuplicate = slug === "total-consolidado-operativo";
      const isInWorkspace = slugsInWorkspace.has(slug);
      const isListStyle = !!button.closest("table");

      if (isInWorkspace) {
        if (!allowDuplicate) {
          markButtonSaved(button, isListStyle);
        } else {
          markButtonInWorkspace(button);
        }
      } else {
        resetButtonToGuardar(button, isListStyle);
      }
    });
  } catch (error) {
    console.error(error);
  }
};

const attachWorkspaceHandlers = () => {
  if (!workspaceApiUrl) {
    return;
  }

  syncWorkspaceState();

  document.addEventListener("click", async (e) => {
    const button = e.target.closest("[data-add-to-workspace]");
    if (!button || button.dataset.saved === "true" || button.dataset.loading === "true") {
      return;
    }
    const slug = button.dataset.reportSlug;
    if (!slug) return;

    button.dataset.loading = "true";
    button.classList.add("opacity-60", "pointer-events-none");
    try {
      const response = await fetch(workspaceApiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          slug,
          allow_duplicate: slug === "total-consolidado-operativo",
        }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "No se pudo guardar el informe");
      }
      const payload = await response.json();
      updateWorkspaceCount(payload.count ?? payload.slots?.length ?? "-");
      if (payload.status === "exists") {
        showToast("Este informe ya está en el workspace", "error");
      } else {
        showToast("Informe guardado en tu workspace");
      }
      await syncWorkspaceState();
    } catch (error) {
      showToast(error.message || "No se pudo guardar", "error");
      button.classList.remove("opacity-60", "pointer-events-none");
      button.dataset.loading = "false";
      await syncWorkspaceState();
    }
  });
};

const attachVisibilityHandlers = () => {
  // La URL correcta es /api/reports/visibility/ según la configuración en django_project/urls.py
  const visibilityApiUrl = "/api/reports/visibility/";
  const toggles = document.querySelectorAll("[data-toggle-visibility]");
  
  toggles.forEach((toggle) => {
    toggle.addEventListener("change", async (e) => {
      const slug = toggle.dataset.reportSlug;
      const isVisible = e.target.checked;
      
      if (!slug) {
        return;
      }
      
      // Deshabilitar el toggle mientras se procesa
      toggle.disabled = true;
      
      try {
        const response = await fetch(visibilityApiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({ slug, is_visible: isVisible }),
        });
        
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "No se pudo cambiar la visibilidad");
        }
        
        const payload = await response.json();
        showToast(
          payload.message || (isVisible 
            ? "Reporte visible para usuarios con puesto Supervisor" 
            : "Reporte oculto para usuarios con puesto Supervisor"),
          "success"
        );
        
        // Actualizar el estado visual del toggle para reflejar el cambio guardado
        if (payload.is_visible !== undefined) {
          e.target.checked = payload.is_visible;
        }
        
        // Nota: El catálogo se actualizará automáticamente al recargar la página
        // Los usuarios con puesto Supervisor verán solo los reportes con is_visible=True
        // El cambio se guarda en la base de datos y se aplicará en la próxima carga del catálogo
      } catch (error) {
        // Revertir el estado del toggle si hay error
        e.target.checked = !isVisible;
        showToast(error.message || "No se pudo cambiar la visibilidad", "error");
      } finally {
        toggle.disabled = false;
      }
    });
  });
};

document.addEventListener("DOMContentLoaded", () => {
  attachWorkspaceHandlers();
  attachVisibilityHandlers();
});
