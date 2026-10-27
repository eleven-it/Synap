/**
 * Utilidades puras del formulario VCM (Vendedor · Cliente · Sucursal · Marca).
 * Usadas por config_vendedor_cliente_marca.html y testeables con Node.
 */
(function (global) {
  const VCM_CHIP_PREVIEW_MAX = 8;

  function vcmFormularioListo(selVend, selCli, selSucs, selMars) {
    const cv = selVend && Number(selVend.CodViajante);
    const ic = selCli && Number(selCli.id_cliente);
    const sucs = Array.isArray(selSucs) ? selSucs : [];
    const mars = Array.isArray(selMars) ? selMars : [];
    if (!cv || cv <= 0) return false;
    if (!ic || ic <= 0) return false;
    if (!sucs.length) return false;
    if (!mars.length) return false;
    for (const s of sucs) {
      const idd = Number(s && s.id_cliente_domicilio);
      if (!idd || idd <= 0) return false;
    }
    for (const m of mars) {
      const cm = Number(m && m.CodMarca);
      if (!cm || cm <= 0) return false;
    }
    return true;
  }

  function vcmBuildCrearPayload(selVend, selCli, selSucs, selMars) {
    if (!vcmFormularioListo(selVend, selCli, selSucs, selMars)) {
      return null;
    }
    return {
      CodViajante: Number(selVend.CodViajante),
      id_cliente: Number(selCli.id_cliente),
      CodMarcas: selMars.map((m) => Number(m.CodMarca)),
      ids_cliente_domicilio: selSucs.map((s) => Number(s.id_cliente_domicilio)),
    };
  }

  function vcmCountRelaciones(selSucs, selMars) {
    const n = (Array.isArray(selSucs) ? selSucs : []).length;
    const m = (Array.isArray(selMars) ? selMars : []).length;
    return n * m;
  }

  function vcmResumenAsignacion(selVend, selCli, selSucs, selMars) {
    const vend = String((selVend && selVend.nombre) || '—').trim() || '—';
    const cli = String((selCli && selCli.nombre) || '—').trim() || '—';
    const ns = (Array.isArray(selSucs) ? selSucs : []).length;
    const nm = (Array.isArray(selMars) ? selMars : []).length;
    const x = vcmCountRelaciones(selSucs, selMars);
    const sucLabel = ns === 1 ? '1 sucursal' : ns + ' sucursales';
    const marLabel = nm === 1 ? '1 marca' : nm + ' marcas';
    const relLabel = x === 1 ? '1 relación' : x + ' relaciones';
    return vend + ' › ' + cli + ' › ' + sucLabel + ' × ' + marLabel + ' = ' + relLabel;
  }

  function vcmChipsPreview(items, maxVisible, expanded) {
    const list = Array.isArray(items) ? items : [];
    const max = Math.max(1, Number(maxVisible) || VCM_CHIP_PREVIEW_MAX);
    if (expanded || list.length <= max) return list;
    return list.slice(0, max);
  }

  function vcmChipsHiddenCount(items, maxVisible, expanded) {
    const list = Array.isArray(items) ? items : [];
    const max = Math.max(1, Number(maxVisible) || VCM_CHIP_PREVIEW_MAX);
    if (expanded || list.length <= max) return 0;
    return list.length - max;
  }

  const api = {
    VCM_CHIP_PREVIEW_MAX,
    vcmFormularioListo,
    vcmBuildCrearPayload,
    vcmCountRelaciones,
    vcmResumenAsignacion,
    vcmChipsPreview,
    vcmChipsHiddenCount,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  global.vcmFormUtils = api;
})(typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : this);
