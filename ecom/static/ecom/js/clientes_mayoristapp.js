/**
 * Listado de clientes mayoristapp — búsqueda predictiva de selección única.
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

  const buscarUrl = root.getAttribute("data-buscar-url");
  const seleccionarUrl = root.getAttribute("data-seleccionar-url");
  const statusEl = document.getElementById("clientes-status");
  const input = document.getElementById("ecom_cliente_search");
  const dropdown = document.getElementById("ecom_cliente_dropdown");
  const predictiveUrl = root.getAttribute("data-predictive-url");
  if (!buscarUrl || !seleccionarUrl || !input || !dropdown || !predictiveUrl) return;

  const { initPredictiveInput, fetchClientesMayoristapp } = await import(predictiveUrl);
  let selecting = false;
  const search = fetchClientesMayoristapp(buscarUrl, 15);
  const searchExpanded = fetchClientesMayoristapp(buscarUrl, 50);
  initPredictiveInput({
    input,
    dropdown,
    minChars: 0,
    emptyMessage: "No se encontraron clientes de tu cartera.",
    fetchItemsExpanded: searchExpanded,
    async fetchItems(query) {
      if (statusEl) statusEl.textContent = "Buscando clientes…";
      try {
        const items = await search(query);
        if (statusEl) statusEl.textContent = items.length
          ? `${items.length} cliente(s) encontrado(s).`
          : "No se encontraron clientes de tu cartera.";
        return items;
      } catch (error) {
        if (statusEl) statusEl.textContent = "No se pudo buscar clientes. Intentá de nuevo.";
        throw error;
      }
    },
    async onPick(item) {
      if (selecting || !item.value) return;
      selecting = true;
      input.disabled = true;
      try {
        const ok = await seleccionarCliente(seleccionarUrl, item.value, statusEl);
        if (!ok) return;
        mostrarPanelSeleccion(item.label);
        const reporteUrl = root.getAttribute("data-reporte-url");
        if (reporteUrl) {
          statusEl.textContent = "Cargando reporte…";
          window.location.assign(reporteUrl);
        }
      } finally {
        selecting = false;
        input.disabled = false;
      }
    },
  });

  if (statusEl) {
    cargarClienteSesion(root, statusEl);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    init().catch(function () {
      const statusEl = document.getElementById("clientes-status");
      if (statusEl) statusEl.textContent = "No se pudo inicializar la búsqueda de clientes.";
    });
  });
} else {
  init().catch(function () {
    const statusEl = document.getElementById("clientes-status");
    if (statusEl) statusEl.textContent = "No se pudo inicializar la búsqueda de clientes.";
  });
}
