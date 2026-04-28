/**
 * Informe Objetivos de venta vs facturación, remitos y BO (jerarquía vendedor → cliente).
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";

  if (reportSlug !== "ventas-objetivos-vs-bo") {
    return;
  }

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

  function escHtml(s) {
    if (s == null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtMoney(v) {
    const n = Number(v);
    if (v == null || v === "" || Number.isNaN(n)) return ARS.format(0);
    return ARS.format(n);
  }

  function fmtNum(v) {
    const n = Number(v);
    if (v == null || v === "" || Number.isNaN(n)) return "0";
    return NUM.format(n);
  }

  function faltaClass(falta) {
    const n = Number(falta);
    if (!Number.isNaN(n) && n < 0) {
      return "text-rose-600 dark:text-rose-400 font-medium";
    }
    return "";
  }

  function facturacionClass(facturacion) {
    const n = Number(facturacion);
    if (!Number.isNaN(n) && n < 0) {
      return "text-rose-600 dark:text-rose-400 font-medium";
    }
    return "";
  }

  function kpiFaltaClass(falta) {
    const n = Number(falta);
    if (Number.isNaN(n)) return "text-slate-900 dark:text-white";
    if (n < 0) return "text-emerald-600 dark:text-emerald-400";
    if (n > 0) return "text-amber-600 dark:text-amber-400";
    return "text-slate-600 dark:text-slate-300";
  }

  function renderKpis(totals) {
    const elObj = document.getElementById("vo-kpi-total-objetivo");
    const elFalta = document.getElementById("vo-kpi-total-falta");
    if (!elObj || !elFalta) return;

    const t = totals && typeof totals === "object" ? totals : {};
    const obj = Number(t.objetivo);
    const fal = Number(t.falta);
    const objN = Number.isFinite(obj) ? obj : 0;
    const falN = Number.isFinite(fal) ? fal : 0;

    elObj.textContent = fmtMoney(objN);
    elObj.className = "text-2xl md:text-3xl font-bold text-slate-900 dark:text-white";

    elFalta.textContent = fmtMoney(falN);
    elFalta.className = "text-2xl md:text-3xl font-bold " + kpiFaltaClass(falN);
  }

  function moneyCells(row) {
    return (
      `<td class="px-2 py-2 text-right whitespace-nowrap">${fmtMoney(row.objetivo)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap ${facturacionClass(row.facturacion)}">${fmtMoney(row.facturacion)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap">${fmtMoney(row.remitos)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap">${fmtMoney(row.total)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap ${faltaClass(row.falta)}">${fmtMoney(row.falta)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap">${fmtNum(row.cantidades_vendidas)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap">${fmtMoney(row.backorder_total)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap">${fmtMoney(row.bo_con_stock)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap">${fmtMoney(row.bo_con_ingreso)}</td>` +
      `<td class="px-2 py-2 text-right whitespace-nowrap">${fmtMoney(row.bo_sin_stock)}</td>`
    );
  }

  function renderTable(jerarquia, totals) {
    const container = document.getElementById("vo-jerarquia-container");
    if (!container) return;

    if (!jerarquia || !jerarquia.length) {
      container.innerHTML =
        '<p class="text-xs text-slate-500 dark:text-slate-400">No hay datos para el período y filtros seleccionados.</p>';
      return;
    }

    /* Fondo opaco (sin /95): si no, las filas del tbody se ven al hacer scroll bajo el sticky. z-30 por encima de las filas. */
    const thSticky =
      "sticky top-0 z-30 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 shadow-[0_1px_0_0_rgb(226_232_240)] dark:shadow-[0_1px_0_0_rgb(51_65_85)]";
    const th =
      "<thead><tr>" +
      `<th class="px-2 py-2 text-left font-semibold ${thSticky} w-8"></th>` +
      `<th class="px-2 py-2 text-left font-semibold ${thSticky} min-w-[12rem]">Vendedor / Cliente</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">Objetivo</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">Facturación</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">Remitos</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">Total</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">Falta</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">Unidades vendidas</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">BO total</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">BO c/stock</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">BO c/ingreso</th>` +
      `<th class="px-2 py-2 text-right font-semibold ${thSticky}">BO s/stock</th>` +
      "</tr></thead>";

    let body = "<tbody>";
    jerarquia.forEach((vend, vi) => {
      const gid = "vo-grp-" + vi;
      body +=
        `<tr class="bg-slate-100/90 dark:bg-slate-800/70 font-semibold cursor-pointer select-none hover:bg-slate-200/80 dark:hover:bg-slate-800" data-vo-toggle="${gid}" role="button" tabindex="0" aria-expanded="false">` +
        `<td class="px-1 py-2 text-center"><span class="vo-chev inline-block text-slate-500" data-chev="${gid}" aria-hidden="true">▸</span></td>` +
        `<td class="px-2 py-2">${escHtml(vend.nombre_vendedor)} <span class="text-slate-500 dark:text-slate-400 font-normal">(${escHtml(vend.cod_viajante)})</span></td>` +
        moneyCells(vend) +
        "</tr>";

      (vend.children || []).forEach((cli) => {
        body +=
          `<tr class="border-b border-slate-100 dark:border-slate-800/80 vo-child-row hidden" data-parent="${gid}">` +
          '<td class="px-1"></td>' +
          `<td class="px-2 py-1.5 pl-6 text-slate-700 dark:text-slate-300">${escHtml(cli.nombre_cliente)} <span class="text-slate-400 dark:text-slate-500 text-[11px]">${escHtml(cli.codigo_cliente)}</span></td>` +
          moneyCells(cli) +
          "</tr>";
      });
    });

    if (totals && typeof totals === "object") {
      body +=
        '<tr class="border-t-2 border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900/50 font-semibold">' +
        '<td class="px-1"></td>' +
        '<td class="px-2 py-2">Totales</td>' +
        moneyCells(totals) +
        "</tr>";
    }

    body += "</tbody>";
    container.innerHTML =
      '<table class="min-w-full text-xs border-separate border-spacing-0 vo-jerarquia-table">' + th + body + "</table>";

    container.querySelectorAll("tr[data-vo-toggle]").forEach((tr) => {
      tr.addEventListener("click", () => toggleGroup(container, tr.getAttribute("data-vo-toggle")));
      tr.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleGroup(container, tr.getAttribute("data-vo-toggle"));
        }
      });
    });
  }

  function toggleGroup(container, gid) {
    if (!gid) return;
    const rows = container.querySelectorAll(`tr[data-parent="${gid}"]`);
    const chev = container.querySelector(`[data-chev="${gid}"]`);
    const header = container.querySelector(`tr[data-vo-toggle="${gid}"]`);
    let collapsed = false;
    rows.forEach((r) => {
      r.classList.toggle("hidden");
      collapsed = r.classList.contains("hidden");
    });
    if (chev) chev.textContent = collapsed ? "▸" : "▾";
    if (header) header.setAttribute("aria-expanded", collapsed ? "false" : "true");
  }

  function processData(payload) {
    const totals = payload.totals || {};
    renderKpis(totals);

    const meta = payload.meta || {};
    const extra = meta.extra || {};
    const tabs = extra.tabs || {};
    const jerarquia = tabs.objetivos_jerarquia || [];
    renderTable(jerarquia, totals);
  }

  window.objetivosVentasBoHandler = { processData: processData };
})();
