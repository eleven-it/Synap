/**
 * Utilidades puras del formulario VCM (Vendedor · Cliente · Sucursal · Marca).
 * Usadas por config_vendedor_cliente_marca.html y testeables con Node.
 */
(function (global) {
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

  const api = {
    vcmFormularioListo,
    vcmBuildCrearPayload,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  global.vcmFormUtils = api;
})(typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : this);
