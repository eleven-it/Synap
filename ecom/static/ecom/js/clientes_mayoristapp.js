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

function iniciarGestionClientes(root, seleccionarUrl, statusEl) {
  const form = document.getElementById("cliente-gestion-form");
  if (!form) return;
  const api = root.dataset.rapidoUrl;
  const mensaje = document.getElementById("cliente-gestion-status");
  const campo = (name) => form.elements.namedItem(name);
  const cargarOpciones = (select, valores, elegido = "") => {
    select.replaceChildren(new Option("Seleccioná…", ""));
    Object.entries(valores || {}).forEach(([id, nombre]) => select.add(new Option(nombre, id)));
    select.value = String(elegido || "");
  };
  const catalogo = async (accion, params = {}) => {
    const url = new URL(api, window.location.origin);
    url.searchParams.set("ajax", "1");
    url.searchParams.set("accion", accion);
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    const response = await fetch(url, { credentials: "same-origin" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "No se pudieron cargar los datos del cliente.");
    return data;
  };
  const provincia = campo("provinciaCliente");
  const departamento = campo("departamentoCliente");
  const distrito = campo("distritoCliente");
  const cargarDepartamentos = async (id = "") => {
    cargarOpciones(departamento, await catalogo("departamento", { idProvincia: provincia.value }), id);
    cargarOpciones(distrito, {});
  };
  const cargarDistritos = async (id = "") => {
    cargarOpciones(distrito, await catalogo("distrito", { idDepartamento: departamento.value }), id);
  };
  provincia.addEventListener("change", () => cargarDepartamentos().catch((e) => { mensaje.textContent = e.message; }));
  departamento.addEventListener("change", () => cargarDistritos().catch((e) => { mensaje.textContent = e.message; }));
  const identidad = ["nombreCliente", "tipoDocCliente", "documentoCliente", "ivaCliente", "tipoCliente"];
  const mostrar = async (codigo = "") => {
    form.reset();
    form.dataset.codigo = codigo;
    document.getElementById("cliente-gestion-titulo").textContent = codigo ? `Editar cliente #${codigo}` : "Nuevo cliente";
    mensaje.textContent = "Cargando datos…";
    form.classList.remove("hidden");
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const inicial = await catalogo("inicio");
      cargarOpciones(campo("ivaCliente"), inicial.ivaCliente);
      cargarOpciones(campo("tipoCliente"), inicial.tipoCliente);
      cargarOpciones(provincia, inicial.provincia);
      cargarOpciones(campo("idTransporte"), inicial.transporte);
      campo("idTransporte").disabled = !!codigo;
      let actual = {};
      if (codigo) actual = (await catalogo("obtieneCliente", { codCliente: codigo })).cliente || {};
      const valores = {
        nombreCliente: actual.nombre_cliente, tipoDocCliente: actual.tipo_doc || "CUIT",
        documentoCliente: actual.CUIT, ivaCliente: actual.IDIva, tipoCliente: actual.TipoCliente,
        telefonoCliente: actual.telefono, emailCliente: actual.Email,
        calleCliente: actual.Calle, numeroCliente: actual.NroCalle, deptoCliente: actual.Dpto,
        provinciaCliente: actual.CodProvincia,
      };
      Object.entries(valores).forEach(([nombre, valor]) => { if (valor != null) campo(nombre).value = String(valor); });
      if (codigo) {
        await cargarDepartamentos(actual.IDDepartamento);
        await cargarDistritos(actual.IDDistrito);
      } else {
        cargarOpciones(departamento, {});
        cargarOpciones(distrito, {});
      }
      identidad.forEach((nombre) => { campo(nombre).disabled = !!codigo && root.dataset.editarIdentidad !== "1"; });
      mensaje.textContent = codigo ? "Editá los datos y guardá los cambios." : "Completá los datos para crear el cliente.";
    } catch (error) { mensaje.textContent = error.message; }
  };
  document.getElementById("cliente-nuevo-abrir")?.addEventListener("click", () => mostrar().catch((e) => { mensaje.textContent = e.message; }));
  document.getElementById("cliente-editar-abrir")?.addEventListener("click", () => mostrar(root.dataset.codigo).catch((e) => { mensaje.textContent = e.message; }));
  document.getElementById("cliente-gestion-cancelar")?.addEventListener("click", () => form.classList.add("hidden"));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const codigo = form.dataset.codigo;
    const data = Object.fromEntries(new FormData(form));
    data.accion = codigo ? "editaCliente" : "altaCliente";
    if (codigo) data.codCliente = codigo;
    if (data.documentoCliente) {
      data[data.tipoDocCliente === "DNI" ? "nroDocCliente" : "nroCuitCliente"] = data.documentoCliente;
    }
    delete data.documentoCliente;
    const boton = form.querySelector('button[type="submit"]');
    boton.disabled = true;
    mensaje.textContent = "Guardando cliente…";
    try {
      const response = await fetch(`${api}?ajax=1`, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
        body: JSON.stringify(data),
      });
      const resultado = await response.json();
      if (!response.ok) throw new Error(resultado.detail || resultado.cartel || "No se pudo guardar el cliente.");
      const id = resultado.codigo || codigo;
      await seleccionarCliente(seleccionarUrl, id, statusEl);
      root.dataset.codigo = String(id);
      mostrarPanelSeleccion(`${data.nombreCliente || campo("nombreCliente").value} (#${id})`);
      cargarTransporte(root, id);
      mensaje.textContent = "Cliente guardado.";
      form.classList.add("hidden");
    } catch (error) { mensaje.textContent = error.message; }
    finally { boton.disabled = false; }
  });
}

async function cargarTransporte(root, codigo) {
  const panel = document.getElementById("cliente-transporte-panel");
  const url = root.getAttribute("data-transporte-url");
  if (!panel || !url || !codigo) return;
  const domicilio = document.getElementById("cliente-transporte-domicilio");
  const transporte = document.getElementById("cliente-transporte-elegido");
  const status = document.getElementById("cliente-transporte-status");
  panel.dataset.codigo = String(codigo);
  status.textContent = "Cargando domicilios y transportes…";
  try {
    const r = await fetch(`${url}?codigo=${encodeURIComponent(codigo)}`, { credentials: "same-origin" });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "No se pudo cargar el transporte.");
    domicilio.replaceChildren();
    transporte.replaceChildren();
    (data.domicilios || []).forEach((d) => {
      const option = document.createElement("option");
      option.value = String(d.id);
      option.textContent = `${d.calle || "Domicilio"} ${d.numero || ""}`.trim();
      option.dataset.transporte = d.id_transporte == null ? "" : String(d.id_transporte);
      domicilio.append(option);
    });
    (data.transportes || []).forEach((t) => {
      const option = document.createElement("option");
      option.value = String(t.id);
      option.textContent = t.nombre || String(t.id);
      transporte.append(option);
    });
    const actualizarElegido = () => {
      const elegido = domicilio.selectedOptions[0]?.dataset.transporte || "";
      transporte.value = elegido;
      if (!transporte.value) transporte.selectedIndex = -1;
    };
    domicilio.onchange = actualizarElegido;
    actualizarElegido();
    panel.classList.remove("hidden");
    status.textContent = domicilio.options.length ? "Seleccioná un domicilio y su transporte." : "Este cliente no tiene domicilios activos.";
  } catch (error) {
    status.textContent = error.message || "No se pudo cargar el transporte.";
  }
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
    root.dataset.codigo = String(cod);
    const label = clienteLabel(lista);
    mostrarPanelSeleccion(label);
    statusEl.textContent = "Cliente activo en sesión.";
    cargarTransporte(root, cod);
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

  const guardarTransporte = document.getElementById("cliente-transporte-guardar");
  iniciarGestionClientes(root, seleccionarUrl, statusEl);
  if (guardarTransporte) guardarTransporte.addEventListener("click", async () => {
    const panel = document.getElementById("cliente-transporte-panel");
    const domicilio = document.getElementById("cliente-transporte-domicilio");
    const transporte = document.getElementById("cliente-transporte-elegido");
    const status = document.getElementById("cliente-transporte-status");
    if (!panel?.dataset.codigo || !domicilio.value || !transporte.value) {
      status.textContent = "Elegí un domicilio y un transporte.";
      return;
    }
    guardarTransporte.disabled = true;
    status.textContent = "Guardando transporte…";
    try {
      const r = await fetch(root.getAttribute("data-transporte-url"), {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
        body: JSON.stringify({ codigo: panel.dataset.codigo, id_domicilio: domicilio.value, id_transporte: transporte.value }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "No se pudo guardar el transporte.");
      await cargarTransporte(root, panel.dataset.codigo);
      status.textContent = "Transporte guardado en la ficha del cliente.";
    } catch (error) {
      status.textContent = error.message || "No se pudo guardar el transporte.";
    } finally {
      guardarTransporte.disabled = false;
    }
  });

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
      document.getElementById("cliente-gestion-form")?.classList.add("hidden");
      const transportePanel = document.getElementById("cliente-transporte-panel");
      if (transportePanel) { transportePanel.classList.add("hidden"); transportePanel.dataset.codigo = ""; }
      try {
        const ok = await seleccionarCliente(seleccionarUrl, item.value, statusEl);
        if (!ok) return;
        mostrarPanelSeleccion(item.label);
        root.dataset.codigo = String(item.value);
        cargarTransporte(root, item.value);
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
