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

const attachWorkspaceHandlers = () => {
  if (!workspaceApiUrl) {
    return;
  }
  const buttons = document.querySelectorAll("[data-add-to-workspace]");
  buttons.forEach((button) => {
    const slug = button.dataset.reportSlug;
    if (!slug) {
      return;
    }
    button.addEventListener("click", async () => {
      if (button.dataset.loading === "true") {
        return;
      }
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
          body: JSON.stringify({ slug }),
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "No se pudo guardar el informe");
        }
        const payload = await response.json();
        updateWorkspaceCount(payload.count ?? "-");
        if (payload.status === "exists") {
          showToast("Este informe ya está en el workspace", "error");
        } else {
          showToast("Informe guardado en tu workspace");
        }
        button.innerHTML = `
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M5 5v14l7-4 7 4V5a2 2 0 00-2-2H7a2 2 0 00-2 2z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Guardado
        `;
      } catch (error) {
        showToast(error.message || "No se pudo guardar", "error");
        button.classList.remove("opacity-60", "pointer-events-none");
        button.dataset.loading = "false";
        return;
      }
    });
  });
};

document.addEventListener("DOMContentLoaded", attachWorkspaceHandlers);
