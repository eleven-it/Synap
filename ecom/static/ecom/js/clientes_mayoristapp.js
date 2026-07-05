/**
 * Listado de clientes mayoristapp — búsqueda predictiva (tags_filter Synap).
 */

function getCookie(name) {
  const v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
  return v ? v.pop() : "";
}

function clienteLabel(c) {
  const cod = c.Codigo != null ? c.Codigo : c.codigo;
  const nombre = (c.nombre_cliente || c.nombre || c.Nombre || "").trim();
  if (cod != null && nombre) return `${nombre} (#${cod})`;
  return nombre || (cod != null ? String(cod) : "—");
}

async function seleccionarCliente(url, codigo, statusEl) {
  if (!url || codigo == null || codigo === "") return false;
  statusEl.textContent = "Guardando cliente en sesión…";
  try {
    const r = await fetch(`${url}?ajax=1`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ codigo: codigo, Codigo: codigo }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      statusEl.textContent = data.detail || "No se pudo seleccionar el cliente.";
      return false;
    }
    statusEl.textContent = "Cliente seleccionado. Ya puede usar el portal y los comprobantes.";
    return true;
  } catch {
    statusEl.textContent = "Error de red al seleccionar el cliente.";
    return false;
  }
}

function mostrarPanelSeleccion(label) {
  const panel = document.getElementById("cliente-seleccion-panel");
  const lab = document.getElementById("cliente-seleccion-label");
  if (lab) lab.textContent = label;
  if (panel) panel.classList.remove("hidden");
}

async function cargarClienteSesion(root, statusEl) {
  const url = root.getAttribute("data-seleccionado-url");
  if (!url) return;
  try {
    const r = await fetch(`${url}?ajax=1`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!r.ok) return;
    const data = await r.json();
    const bag = data.cliente || data;
    const lista = Array.isArray(bag) ? bag[0] : bag;
    if (!lista || typeof lista !== "object") return;
    const cod = lista.Codigo != null ? lista.Codigo : lista.codigo;
    if (cod == null) return;
    const label = clienteLabel(lista);
    mostrarPanelSeleccion(label);
    statusEl.textContent = "Cliente activo en sesión.";
  } catch {
    /* sin cliente previo */
  }
}

async function init() {
  const root = document.getElementById("clientes-app");
  if (!root) return;

  const tagsUrl = root.getAttribute("data-tags-filter-url");
  if (!tagsUrl) return;

  const mod = await import(tagsUrl);
  const initializeTagsFilter = mod.initializeTagsFilter;

  const buscarUrl = root.getAttribute("data-buscar-url");
  const seleccionarUrl = root.getAttribute("data-seleccionar-url");
  const statusEl = document.getElementById("clientes-status");

  initializeTagsFilter("ecom_cliente", "cliente", null, {
    maxSelections: 1,
    remoteSearch: {
      minChars: 2,
      fetchFn(q) {
        const params = new URLSearchParams({
          ajax: "1",
          modoBus: "texto",
          patron: q,
          q: q,
          limit: "15",
        });
        return fetch(`${buscarUrl}?${params}`, {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        })
          .then((res) => {
            if (!res.ok) {
              return res.json().then((err) => {
                const msg = (err && err.detail) || "Error al buscar clientes.";
                if (statusEl) statusEl.textContent = msg;
                throw new Error(msg);
              });
            }
            return res.json();
          })
          .then((data) => {
            const rows = data.results || data.clientes || [];
            if (statusEl) {
              statusEl.textContent =
                rows.length > 0
                  ? `${rows.length} cliente(s) encontrado(s).`
                  : "No se encontraron clientes para esa búsqueda.";
            }
            return rows.map((c) => {
              const cod = c.id != null ? c.id : c.Codigo != null ? c.Codigo : c.codigo;
              const nombre = c.text || c.nombre_cliente || c.nombre || "";
              const label = nombre ? `${nombre} (#${cod})` : String(cod);
              return { value: String(cod), label };
            });
          });
      },
    },
  });

  const select = document.getElementById("ecom_cliente");
  if (select) {
    select.addEventListener("change", () => {
      const cod = Array.from(select.selectedOptions)
        .map((o) => o.value)
        .find(Boolean);
      if (!cod) return;
      const opt = select.querySelector(`option[value="${CSS.escape(cod)}"]`);
      const label = opt ? opt.textContent : cod;
      seleccionarCliente(seleccionarUrl, cod, statusEl).then((ok) => {
        if (ok) mostrarPanelSeleccion(label);
      });
    });
  }

  if (statusEl) {
    cargarClienteSesion(root, statusEl);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    init().catch(function () {
      const statusEl = document.getElementById("clientes-status");
      if (statusEl) statusEl.textContent = "No se pudo inicializar la búsqueda predictiva.";
    });
  });
} else {
  init().catch(function () {
    const statusEl = document.getElementById("clientes-status");
    if (statusEl) statusEl.textContent = "No se pudo inicializar la búsqueda predictiva.";
  });
}
