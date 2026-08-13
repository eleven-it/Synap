/** Utilidades de fechas cabecera comercial (dd/MM/yyyy ↔ ISO). */

export function isoToDisplay(iso) {
  if (!iso) return '';
  const parts = String(iso).split('-');
  if (parts.length !== 3) return '';
  const [y, m, d] = parts;
  return `${d.padStart(2, '0')}/${m.padStart(2, '0')}/${y}`;
}

export function displayToIso(display) {
  const m = String(display || '').trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!m) return null;
  return `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
}

export function addDaysIso(iso, dias) {
  if (!iso) return null;
  const d = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  d.setDate(d.getDate() + Number(dias || 0));
  return d.toISOString().slice(0, 10);
}

export function cabeceraConDisplay(raw) {
  if (!raw || raw.error) return null;
  return {
    fecha_pedido: raw.fecha_pedido,
    fecha_entrega: raw.fecha_entrega,
    vencimiento: raw.vencimiento,
    fecha_pedido_display: isoToDisplay(raw.fecha_pedido),
    fecha_entrega_display: isoToDisplay(raw.fecha_entrega),
    vencimiento_display: isoToDisplay(raw.vencimiento),
    id_condventa: raw.id_condventa,
    cond_venta: raw.cond_venta,
    lista_id: raw.lista_id,
    dias_condicion: raw.dias_condicion || 0,
  };
}

export function payloadCabeceraApi(cabecera, puedeEditarOFlags) {
  if (!cabecera) return {};
  const flags = (puedeEditarOFlags && typeof puedeEditarOFlags === 'object')
    ? puedeEditarOFlags
    : {
        puedeEditar: !!puedeEditarOFlags,
        puedeEditarLista: !!puedeEditarOFlags,
        puedeEditarCondicion: !!puedeEditarOFlags,
        puedeEditarVencimiento: !!puedeEditarOFlags,
      };
  const fp = cabecera.fecha_pedido || displayToIso(cabecera.fecha_pedido_display);
  const fe = cabecera.fecha_entrega || displayToIso(cabecera.fecha_entrega_display);
  const ven = cabecera.vencimiento || displayToIso(cabecera.vencimiento_display);
  const out = {
    fecha_pedido: fp,
    fecha_entrega: fe || undefined,
  };
  if (flags.puedeEditarVencimiento || flags.puedeEditar) {
    out.vencimiento = ven;
  }
  if (flags.puedeEditarCondicion || flags.puedeEditar) {
    out.id_condventa = cabecera.id_condventa;
  }
  if (flags.puedeEditarLista || flags.puedeEditar) {
    out.lista_id = cabecera.lista_id;
  }
  return out;
}
