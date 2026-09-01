# 06 — Patrones de Formulario

**Estado:** COMPLETE

## Patrones observados

| Pattern | Canon location | Adoption |
|---------|----------------|----------|
| Labels above field | MPR, core usuarios | Wide |
| Required | `*` o validación server | Inconsistent |
| Toggle Sí/No | `btn-toggle-estado-usuario` | Canon usuarios/sucursales |
| Post-loading on submit | `mpr-post-loading` class | MPR, contabilidad |
| CSRF | `{% csrf_token %}` | Universal Django |
| Multi-step | MPR wizard, TN config wizard | Specialized |
| AJAX save | ecom hub, reports builder | Partial |

## Inconsistencias

- Help text: ausente en mayoría; algunos MPR tooltips inline
- Errors: Django messages (top) vs field errors (inline) — mixed
- Save/Cancel: posición variable (top-right vs bottom bar)
- Autosave: solo drafts pedido masivo (PG)
- Double-submit: post-loading modal mitiga en MPR; **no universal**

## Errores detectados (código)

| Issue | Evidence |
|-------|----------|
| Error lejos del campo | Django messages global pattern |
| Validación silenciosa AJAX | algunos fetch sin error UI en ecom |
| Valor perdido en error | standard Django re-render — OK en forms server |
| Doble click save | mitigado solo con post-loading |

## Target pattern (no implementar aún)

FormField + FormActions + inline errors + SynapMessages for success — aligned with design system target.
