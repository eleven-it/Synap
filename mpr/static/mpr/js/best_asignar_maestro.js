/**
 * Autocomplete genérico para asignación manual en Migración BEST.
 * Uso Alpine: x-data="bestAsignarMaestro(url, { idKey, labelKey, stateKey, metaLine, emptyMsg })"
 */
function bestAsignarMaestro(searchUrl, cfg) {
  cfg = cfg || {};
  const idKey = cfg.idKey || 'id';
  const labelKey = cfg.labelKey || 'text';
  const stateKey = cfg.stateKey || 'selectedId';
  const metaLine = typeof cfg.metaLine === 'function' ? cfg.metaLine : null;
  const emptyMsg = cfg.emptyMsg || 'Elegí un ítem de la lista.';
  const queryParams = cfg.queryParams && typeof cfg.queryParams === 'object' ? cfg.queryParams : {};
  const MAX_PANEL_H = 280;

  const state = {
    q: '',
    resultados: [],
    dropdown: false,
    loading: false,
    error: false,
    errorMsg: '',
    highlighted: -1,
    panelStyle: '',
  };
  state[stateKey] = '';

  state.metaDe = function (item) {
    if (metaLine) return metaLine(item) || '';
    return String(item[idKey] != null ? item[idKey] : '');
  };

  state.actualizarPanel = function () {
    const el = this.$refs.wrap;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const width = Math.max(r.width, 280);
    let left = r.left;
    if (left + width > window.innerWidth - 8) {
      left = Math.max(8, window.innerWidth - width - 8);
    }
    const gap = 4;
    const spaceBelow = window.innerHeight - r.bottom - 8;
    const spaceAbove = r.top - 8;
    const openUp = spaceBelow < 160 && spaceAbove > spaceBelow;
    const avail = openUp ? spaceAbove : spaceBelow;
    const maxH = Math.max(120, Math.min(MAX_PANEL_H, avail));
    if (openUp) {
      this.panelStyle =
        'bottom:' +
        Math.round(window.innerHeight - r.top + gap) +
        'px;top:auto;left:' +
        Math.round(left) +
        'px;width:' +
        Math.round(width) +
        'px;max-height:' +
        Math.round(maxH) +
        'px;overflow-y:auto;';
    } else {
      this.panelStyle =
        'top:' +
        Math.round(r.bottom + gap) +
        'px;bottom:auto;left:' +
        Math.round(left) +
        'px;width:' +
        Math.round(width) +
        'px;max-height:' +
        Math.round(maxH) +
        'px;overflow-y:auto;';
    }
  };

  state.scrollHighlightedIntoView = function () {
    const self = this;
    this.$nextTick(function () {
      const panel = self.$refs.panel;
      if (!panel || self.highlighted < 0) return;
      const item = panel.querySelector('[data-best-opt-idx="' + self.highlighted + '"]');
      if (item && typeof item.scrollIntoView === 'function') {
        item.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      }
    });
  };

  state.buscar = async function () {
    const termino = this.q.trim();
    this.errorMsg = '';
    if (!termino) {
      this.resultados = [];
      this.dropdown = false;
      this.highlighted = -1;
      return;
    }
    if (this[stateKey]) {
      this[stateKey] = '';
    }
    this.loading = true;
    this.error = false;
    this.actualizarPanel();
    try {
      const params = new URLSearchParams();
      params.set('q', termino);
      params.set('limit', '15');
      Object.keys(queryParams).forEach(function (k) {
        if (queryParams[k] != null && queryParams[k] !== '') {
          params.set(k, String(queryParams[k]));
        }
      });
      const r = await fetch(searchUrl + '?' + params.toString(), {
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (!r.ok) {
        throw new Error('HTTP ' + r.status);
      }
      const data = await r.json();
      this.resultados = data.results || [];
      this.dropdown = true;
      this.highlighted = this.resultados.length ? 0 : -1;
      this.$nextTick(() => {
        this.actualizarPanel();
        this.scrollHighlightedIntoView();
      });
    } catch (e) {
      this.resultados = [];
      this.dropdown = true;
      this.error = true;
      this.highlighted = -1;
    }
    this.loading = false;
  };

  state.seleccionar = function (item) {
    if (!item || item[idKey] == null || item[idKey] === '') return;
    this[stateKey] = String(item[idKey]);
    this.q = item[labelKey] || String(item[idKey]);
    this.resultados = [];
    this.dropdown = false;
    this.highlighted = -1;
    this.errorMsg = '';
  };

  state.cerrar = function () {
    this.dropdown = false;
    this.highlighted = -1;
  };

  state.onOutside = function (e) {
    if (this.$refs.wrap && this.$refs.wrap.contains(e.target)) return;
    if (this.$refs.panel && this.$refs.panel.contains(e.target)) return;
    this.cerrar();
  };

  state.onKeydown = function (e) {
    if (e.key === 'Escape') {
      this.cerrar();
      return;
    }
    if (!this.dropdown || !this.resultados.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.highlighted = Math.min(this.highlighted + 1, this.resultados.length - 1);
      this.scrollHighlightedIntoView();
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.highlighted = Math.max(this.highlighted - 1, 0);
      this.scrollHighlightedIntoView();
      return;
    }
    if (e.key === 'Enter' && this.highlighted >= 0 && this.resultados[this.highlighted]) {
      e.preventDefault();
      this.seleccionar(this.resultados[this.highlighted]);
    }
  };

  state.validarSubmit = function (e) {
    if (!this[stateKey]) {
      e.preventDefault();
      this.errorMsg = emptyMsg;
    }
  };

  return state;
}

function bestAsignarArticulo(searchUrl) {
  return bestAsignarMaestro(searchUrl, {
    idKey: 'IDArt',
    labelKey: 'Descripcion',
    stateKey: 'adminIdart',
    emptyMsg: 'Elegí un artículo de la lista.',
    queryParams: { tipo_art_fab: 'Terminado' },
    metaLine: function (a) {
      // Solo descripción visible en el listado; sin códigos en la línea principal.
      return '';
    },
  });
}

function bestAsignarDeposito(searchUrl) {
  return bestAsignarMaestro(searchUrl, {
    idKey: 'CodDeposito',
    labelKey: 'NombreDeposito',
    stateKey: 'adminCodDeposito',
    emptyMsg: 'Elegí un depósito de la lista.',
    metaLine: function (d) {
      var parts = ['Cod ' + (d.CodDeposito != null ? d.CodDeposito : '—')];
      if (d.tipo_mpr) parts.push(d.tipo_mpr);
      return parts.join(' · ');
    },
  });
}

function bestAsignarCliente(searchUrl) {
  return bestAsignarMaestro(searchUrl, {
    idKey: 'Codigo',
    labelKey: 'Nombre',
    stateKey: 'adminCodigo',
    emptyMsg: 'Elegí un cliente de la lista.',
    metaLine: function (c) {
      var parts = ['Código ' + (c.Codigo != null ? c.Codigo : '—')];
      if (c.CUIT && c.CUIT !== '-') parts.push(c.CUIT);
      if (c.id_manual_cli && c.id_manual_cli !== '-') parts.push(c.id_manual_cli);
      return parts.join(' · ');
    },
  });
}

function bestSeleccionLote() {
  return {
    n: 0,
    refresh() {
      this.n = this.$root.querySelectorAll('input.best-sel-row:checked').length;
    },
    toggleAll(ev) {
      const on = !!(ev && ev.target && ev.target.checked);
      this.$root.querySelectorAll('input.best-sel-row').forEach(function (el) {
        el.checked = on;
      });
      this.refresh();
    },
  };
}
