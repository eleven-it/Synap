# Plan UI/UX — captura y revisión de facturas de compra (PWA + desktop)

**Alcance:** cuándo y cómo entra el diseño sin bloquear ni ser bloqueado por el posting legacy.  
**Alineado a:** [product_requirements.md](product_requirements.md) §9–10, [architecture.md](architecture.md), [master_execution_plan.md](master_execution_plan.md).

**Convención:** *Decisión nueva de producto/UX* | *Confirmado por auditoría* (solo para etiquetas/ flujos equivalentes al VB6 a nivel conceptual, no para UI pixel-perfect del legacy).

---

## 1. ¿Cuándo entra UI/UX?

| Momento | Actividad UX | Dependencia backend |
|---------|--------------|---------------------|
| **Durante Fase 0** | Kickoff UX: personas, journey de analista y capturador; principios mobile-first | Ninguna |
| **En paralelo con Fase 1** | Wireframes baja fidelidad + flujo de estados; mapa de pantallas MVP | API puede ser mock (OpenAPI stub) o contratos JSON acordados |
| **Fase 2** | Prototipo navegable ingesta (cámara/PDF); feedback en dispositivos reales | Endpoints reales de upload + job status |
| **Fase 3** | UI alta fidelidad formularios cabecera/líneas; accesibilidad y copy | API expediente + validaciones servidor |
| **Fase 4+** | Pantallas de resultado posting (éxito/error); mensajes de rollback | Respuesta real `LegacyPostingResult` / `Failure` |

**Regla:** ningún diseño final de «Aprobar» debe asumir datos que el `LegacyPostingCommand` no pueda llevar; revisión conjunta con backend usando [posting_contract.md](posting_contract.md).

---

## 2. Qué UX se hace antes del backend completo

- **Sí antes:** flujos, wireframes, design tokens compartidos con Synap, empty states, errores genéricos, lista de expedientes, estados visuales (badges).
- **No antes (o solo con mock):** validaciones de negocio dependientes de maestros legacy (proveedor/artículo) en tiempo real — usar **autocomplete stub** o datos semilla hasta integrar APIs existentes del core.

---

## 3. Entregables UX por fase

| Fase | Entregable UX |
|------|----------------|
| 0 | Documento 1 página: objetivos UX + no objetivos |
| 1 | Wireframes: lista, detalle vacío, creación manual expediente |
| 2 | Wireframes/prototipo: captura cámara/PDF, estado «OCR en curso» |
| 3 | UI componentes: formulario cabecera, tabla líneas, rechazo con motivo, confirmación aprobar |
| 4 | Pantalla éxito (nro comprobante, cod mov); pantalla error posting + reintento |
| 5 | Pulido responsive, offline shell (opcional), loading states |
| 6 | Guía breve usuario + capturas |

---

## 4. Wireframes requeridos (MVP)

1. **Lista expedientes** (filtros: estado, fecha, proveedor).
2. **Detalle expediente** (pestañas o secciones: documento, datos, líneas, historial).
3. **Nuevo** — elección cámara vs PDF.
4. **Captura** — preview archivo + confirmar subida.
5. **Borrador** — mensaje OCR pendiente / fallido / listo.
6. **Revisión** — edición cabecera y líneas.
7. **Rechazar** — modal motivo obligatorio.
8. **Aprobar** — modal confirmación con resumen (sin prometer ERP hasta éxito).
9. **Resultado** — éxito posting vs error (códigos amigables según [posting_contract.md](posting_contract.md)).

---

## 5. Flujos clave a diseñar primero

1. **Crear borrador** → subir archivo → ver estado job OCR.
2. **OCR fallido** → continuar edición manual (sin bloquear).
3. **Enviar a revisión** → notificación opcional (fuera de MVP si no hay infra).
4. **Aprobar** (con stub): mismo flujo visual que producción; backend devuelve fake `codigo_movimiento`.
5. **Aprobar** (real Fase 4): mismas pantallas; copy actualizado.

---

## 6. Pantallas mínimas MVP (usuario final)

- Lista + detalle + nuevo + captura + revisión + rechazo + aprobar + resultado.
- **Login / permisos:** reutilizar shell Synap existente si aplica (*decisión nueva de arquitectura* según repo).

---

## 7. Pantallas que pueden esperar (post-MVP)

- Asignación analista por cola.
- Dashboard métricas OCR.
- Búsqueda avanzada full-text.
- Modo offline completo.
- Integración visual con asiento contable / CC (post-commit VB6 equivalente).

---

## 8. Sincronizar UI con dominio sin posting real

- **Contrato API:** estados del PRD alineados a `ExpedienteFacturaCompra` en [domain_model.md](domain_model.md); documento OpenAPI o schema JSON versionado en repo.
- **Botón Aprobar:** en Fase 1–3 llama a endpoint que:
  - valida transición; y
  - si `settings.POSTING_BACKEND=fake`, devuelve `LegacyPostingResult` sintético; si `noop`, deja `listo_para_poster` o estado intermedio acordado (*definir en implementación — documentar en ADR corto si diverge del PRD*).
- **Mapper UI → Command:** tabla de campos pantalla ↔ `LegacyPostingCommand` mantenida junto al código del mapper (test unitario obligatorio).

---

## 9. Referencias cruzadas

- DoD por fase: [definition_of_done_by_phase.md](definition_of_done_by_phase.md)
- Decisiones abiertas que afectan UX (OCR, storage): [open_decisions_checklist.md](open_decisions_checklist.md)
