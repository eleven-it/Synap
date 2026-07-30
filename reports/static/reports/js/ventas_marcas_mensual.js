/**
 * Informe Ventas marcas mensual: KPIs + matriz Ven → Cliente × AñoMes.
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "ventas-marcas-mensual") {
    return;
  }

  const VIEW_STATE_KEY = `synap:report-view:${reportSlug}:expanded`;
  const CHV = { expandido: "▾", colapsado: "▸" };

  const ARS = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const NUM = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

  const MESES_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
  ];

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtMoney(v) {
    const n = Number(v);
    return Number.isFinite(n) ? ARS.format(n) : "—";
  }

  function fmtNum(v) {
    const n = Number(v);
    return Number.isFinite(n) ? NUM.format(n) : "—";
  }

  function fmtMesYm(ym) {
    const s = String(ym || "");
    if (s.length !== 6) return s;
    const y = s.slice(0, 4);
    const m = parseInt(s.slice(4, 6), 10);
    if (m < 1 || m > 12) return s;
    return `${MESES_ES[m - 1]} ${y}`;
  }

  function loadExpandedVendedores() {
    try {
      const raw = window.localStorage.getItem(VIEW_STATE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function saveExpandedVendedores(map) {
    try {
      window.localStorage.setItem(VIEW_STATE_KEY, JSON.stringify(map || {}));
    } catch (e) {
      /* sin localStorage */
    }
  }

  function renderKpis(extra) {
    const kpis = extra?.kpis || {};
    const modo = extra?.modo_unidades || "packs";
    const unidadLabel = modo === "docenas" ? "Docenas" : "Unidades";
    const elU = document.getElementById("vmm-kpi-unidades");
    const elF = document.getElementById("vmm-kpi-facturacion");
    const elP = document.getElementById("vmm-kpi-precio-medio");
    const elR = document.getElementById("vmm-kpi-regalias");
    const elRtc = document.getElementById("vmm-kpi-regalias-tc");
    const elUL = document.getElementById("vmm-kpi-unidades-label");
    if (elUL) elUL.textContent = unidadLabel;
    if (elU) elU.textContent = fmtNum(kpis.unidades);
    if (elF) elF.textContent = fmtMoney(kpis.facturacion);
    if (elP) elP.textContent = fmtMoney(kpis.precio_medio);
    if (elR) elR.textContent = fmtMoney(kpis.regalias);
    if (elRtc) elRtc.textContent = fmtNum(kpis.regalias_tc);
  }

  function renderAviso(extra, notes) {
    const el = document.getElementById("vmm-aviso-meses");
    if (!el) return;
    const msg = extra?.aviso_meses || (Array.isArray(notes) ? notes.find(Boolean) : "") || "";
    if (msg) {
      el.textContent = msg;
      el.classList.remove("hidden");
    } else {
      el.textContent = "";
      el.classList.add("hidden");
    }
  }

  function renderCeldasMes(c, proyActiva, proyCls) {
    const base = c || { u: 0, f: 0 };
    let html = `<td class="px-1 py-1.5 text-right tabular-nums border-l border-slate-100 dark:border-slate-700/60">${fmtNum(base.u)}</td>`;
    html += `<td class="px-1 py-1.5 text-right tabular-nums">${fmtMoney(base.f)}</td>`;
    if (proyActiva) {
      html += `<td class="px-1 py-1.5 text-right tabular-nums ${proyCls}">${fmtNum(base.pu ?? 0)}</td>`;
      html += `<td class="px-1 py-1.5 text-right tabular-nums ${proyCls}">${fmtMoney(base.pf ?? 0)}</td>`;
    }
    return html;
  }

  function renderMatriz(extra) {
    const container = document.getElementById("vmm-matriz-container");
    if (!container) return;

    const meses = Array.isArray(extra?.meses) ? extra.meses : [];
    const filas = Array.isArray(extra?.filas) ? extra.filas : [];
    const expanded = loadExpandedVendedores();
    const proyActiva = Boolean(extra?.proyeccion?.activa);
    const colspanMes = proyActiva ? 4 : 2;
    const proyCls = "text-slate-500 dark:text-slate-400";

    if (!meses.length) {
      container.innerHTML = '<p class="px-3 py-4 text-xs text-slate-500 dark:text-slate-400">Sin datos para el período y filtros seleccionados.</p>';
      return;
    }

    const unidadHdr = extra?.modo_unidades === "docenas" ? "Doc." : "U.";

    let thead = `<thead class="sticky top-0 z-10 bg-slate-100 dark:bg-slate-900"><tr>`;
    thead += `<th class="px-2 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300 min-w-[220px]">Vendedor / Cliente</th>`;
    meses.forEach((m) => {
      thead += `<th colspan="${colspanMes}" class="px-1 py-2 text-center text-[10px] font-semibold uppercase text-slate-600 dark:text-slate-300 border-l border-slate-200 dark:border-slate-700">${escHtml(fmtMesYm(m))}</th>`;
    });
    thead += `<th colspan="${colspanMes}" class="px-1 py-2 text-center text-[10px] font-semibold uppercase text-slate-700 dark:text-slate-200 border-l border-slate-300 dark:border-slate-600 bg-slate-200/80 dark:bg-slate-800">Total</th>`;
    thead += `</tr><tr>`;
    thead += `<th class="px-2 py-1"></th>`;
    const subHdr = () => {
      let h = `<th class="px-1 py-1 text-right text-[9px] text-slate-500">${unidadHdr}</th><th class="px-1 py-1 text-right text-[9px] text-slate-500">$</th>`;
      if (proyActiva) {
        h += `<th class="px-1 py-1 text-right text-[9px] text-slate-400">${unidadHdr} proy</th><th class="px-1 py-1 text-right text-[9px] text-slate-400">$ proy</th>`;
      }
      return h;
    };
    meses.forEach(() => {
      thead += subHdr();
    });
    thead += subHdr().replace(/text-slate-500/g, "text-slate-600 font-semibold");
    thead += `</tr></thead>`;

    let tbody = "<tbody>";
    filas.forEach((vend) => {
      const vkey = String(vend.cod ?? "");
      const isExp = Boolean(expanded[vkey]);
      const chev = isExp ? CHV.expandido : CHV.colapsado;
      tbody += `<tr class="bg-slate-50 dark:bg-slate-800/80 font-semibold text-xs text-slate-800 dark:text-slate-100 border-t border-slate-200 dark:border-slate-700">`;
      tbody += `<td class="px-2 py-1.5"><button type="button" class="vmm-vend-toggle inline-flex items-center gap-1 text-left hover:text-sky-600 dark:hover:text-sky-400" data-vend-key="${escHtml(vkey)}" aria-expanded="${isExp}"><span aria-hidden="true">${chev}</span><span>${escHtml(vend.nombre || vkey)}</span></button></td>`;
      meses.forEach((m) => {
        const c = (vend.totales_mes || {})[m] || { u: 0, f: 0 };
        tbody += renderCeldasMes(c, proyActiva, proyCls).replace(/py-1\.5/g, "py-1.5");
      });
      const tot = vend.total || { u: 0, f: 0 };
      tbody += renderCeldasMes(tot, proyActiva, `${proyCls} font-semibold`).replace(
        "border-l border-slate-100",
        "border-l border-slate-200 dark:border-slate-600 font-semibold"
      );
      tbody += `</tr>`;

      if (isExp) {
        (vend.clientes || []).forEach((cli) => {
          tbody += `<tr class="text-[11px] text-slate-700 dark:text-slate-300">`;
          tbody += `<td class="px-2 py-1 pl-8">${escHtml(cli.nombre || cli.cod)}</td>`;
          meses.forEach((m) => {
            const c = (cli.valores_mes || {})[m] || { u: 0, f: 0 };
            tbody += renderCeldasMes(c, proyActiva, proyCls).replace(/py-1\.5/g, "py-1");
          });
          const ct = cli.total || { u: 0, f: 0 };
          tbody += renderCeldasMes(ct, proyActiva, proyCls).replace(
            "border-l border-slate-100",
            "border-l border-slate-100 dark:border-slate-700"
          );
          tbody += `</tr>`;
        });
      }
    });
    tbody += "</tbody>";

    container.innerHTML = `<table class="vmm-matriz-table w-full min-w-max border-collapse text-xs">${thead}${tbody}</table>`;

    container.querySelectorAll(".vmm-vend-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-vend-key") || "";
        const map = loadExpandedVendedores();
        map[key] = !map[key];
        saveExpandedVendedores(map);
        renderMatriz(extra);
      });
    });
  }

  function processData(response) {
    const meta = response?.meta || {};
    const extra = meta.extra || {};
    renderKpis(extra);
    renderAviso(extra, response?.notes);
    renderMatriz(extra);

    const periodEl = document.getElementById("vmm-summary-period");
    if (periodEl) {
      const fa = meta.filters_applied || {};
      const fmt = (s) => {
        if (!s) return "—";
        const p = String(s).split("-");
        return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : s;
      };
      periodEl.textContent = `Período: ${fmt(fa.fecha_inicio_facturacion)} al ${fmt(fa.fecha_fin_facturacion)}`;
    }
  }

  window.ventasMarcasMensualHandler = { processData };
})();
