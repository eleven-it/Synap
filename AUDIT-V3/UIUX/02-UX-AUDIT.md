# 02 — Auditoría UX

**Estado:** COMPLETE | Por workflow crítico

| Workflow | Discoverability | Clarity | Efficiency | Feedback | Error prev. | Recovery | Consistency | Cognitive load |
|----------|:---------------:|:-------:|:----------:|:--------:|:-----------:|:--------:|:-------------:|:----------------:|
| Login | Alta | Alta | Media (3 campos) | Media | Media | Alta | Alta | Baja |
| Pedido hub | Media | Media | Alta (kanban) | Alta (toasts) | Media | Media | Media | **Alta** |
| MPR wizard | Media | Media-Alta | Media (4 pasos) | Alta (mprShowAviso) | Media | Baja | Alta en MPR | Alta |
| TPV kiosco | Alta | Alta | **Muy alta** | Media | Media | Baja | Media | Baja |
| Reports dashboard | Media | Media | Alta (filtros) | Media | Baja | Media | Alta en reports | **Alta** |
| Stock conteo móvil | Media (PWA) | Alta | Alta | Media | Media | Media | Media | Baja |
| TN config | Baja | Baja | Baja (wizard largo) | Media | Baja | Media | Baja | **Alta** |

## Hallazgos transversales

1. **Eficiencia ERP preservada** en TPV y tablas MPR — no degradar por minimalismo.
2. **Feedback dual:** SynapMessages (global) vs mprShowAviso (MPR) vs inline — inconsistente fuera canon.
3. **Discoverability baja** en integraciones (TN, Odoo) — enterradas en menú.
4. **Recovery débil** en producción (wizard) — errores stock requieren supervisor.
5. **Old-looking ≠ bad UX** — tablas compactas MPR son eficientes para operarios.

## Regla UX (evidencia-based)

Conservar densidad informativa y shortcuts en flujos operativos; mejorar consistencia de feedback y navegación en flujos administrativos.
