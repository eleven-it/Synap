# Test strategy: TDD para captura y posting de facturas de compra

**Referencias:** [product_requirements.md](product_requirements.md), [legacy_integration_spec.md](legacy_integration_spec.md), [auditoria_facturas_compras_reglas_negocio.md](auditoria_facturas_compras_reglas_negocio.md), ADRs [adrs/](adrs/).

**Convención:** *Confirmado por auditoría* | *Decisión nueva de QA* | *Riesgo pendiente*

---

## 1. Objetivos del testing

1. **Paridad funcional** del posting con el circuito documentado en la auditoría VB6. *Confirmado por auditoría* como criterio de corrección.
2. **Seguridad de regresión** ante cambios en OCR/workflow sin romper MySQL legacy. *Decisión nueva.*
3. **TDD:** escribir tests que fallen antes de implementar cada capability ([test_cases.md](test_cases.md)).

---

## 2. Pirámide de pruebas

| Nivel | Alcance | Herramientas (propuesta) |
|-------|---------|---------------------------|
| **Unit** | Value objects, máquina de estados expediente, mappers DTO→Command, formateo `NroComprobante` | pytest, Django TestCase aislado |
| **Integration (Synap DB)** | Repositorios expediente, transiciones, idempotencia aprobación | pytest-django, DB test |
| **Integration (MySQL legacy)** | `LegacyPostingAdapter` contra schema fixture | pytest + MySQL testcontainer o DB dedicada |
| **End-to-end** | API + worker OCR mock + posting | Playwright opcional fase tardía |
| **Contract / regression audit** | Checklist trazado a sección de auditoría | Tabla en CI (markdown o JSON) |

---

## 3. TDD por capability (plantilla obligatoria)

Para cada capability en [test_cases.md](test_cases.md):

| Campo | Contenido |
|-------|-----------|
| **Comportamiento esperado** | Qué debe hacer el sistema |
| **Precondiciones** | Estado DB, permisos, flags |
| **Entrada** | DTO / HTTP / archivo |
| **Efectos esperados** | Filas/columnas o estados |
| **Side effects legacy** | Tablas tocadas (*confirmado por auditoría*) |
| **Casos borde** | Mínimo 2 por capability |
| **Rollback esperado** | Ningún cambio en MySQL si falla |
| **Evidencia auditoría** | Archivo + sección o JSON spec |

---

## 4. Boundaries: fake vs real DB

### 4.1 Synap (PostgreSQL/SQLite tests)

- **Siempre real** en integration tests de workflow (transacciones `atomic`).

### 4.2 MySQL legacy

- **Unit tests del adapter:** mock de conexión / spy de sentencias ejecutadas (verificar orden y parámetros).
- **Integration tests críticos:** MySQL real con schema mínimo y datos semilla (*decisión nueva*).
- **No** usar producción; *riesgo pendiente* anonimización si se clona schema cliente.

---

## 5. Estrategia de fixtures

| Fixture | Contenido |
|---------|-----------|
| `proveedor_minimo` | `proveedor` con saldo conocido |
| `cond_venta_contado` / `_credito` | `Dias = 0` vs `<> 0` (*confirmado por auditoría*) |
| `articulo_deposito` | `articulo`, `stock_deposito` fila |
| `periodo_abierto` | `periodos`+`years` coherente con fechas test |
| `codmov_inicial` | Valor base para asserts de incremento |
| `cont_paramatriz_stub` | Mínimo para asiento si tests contabilidad |

Generación: migraciones MySQL de test + `pytest` fixtures en código Python que insertan vía SQL o Django secondary connection.

---

## 6. Tests de workflow (sin legacy)

- Transiciones de estado inválidas deben fallar.
- Rechazo no dispara posting (mock `LegacyPostingAdapter` nunca llamado).
- Doble clic «Aprobar»: segundo intento idempotente o error controlado (*decisión nueva* — definir en implementación; tests deben fijar comportamiento).

---

## 7. Tests de posting (con legacy)

Alineados a [auditoria_facturas_compras_tablas_campos.md](auditoria_facturas_compras_tablas_campos.md) §10 y Anexo A:

- Assert **orden** de llamadas o de existencia de filas tras commit (si se usa DB real).
- Assert **no filas** tras rollback simulado (excepción a mitad de cadena).

---

## 8. Regresión basada en auditoría

Mantener tabla versionada (p. ej. en `test_cases.md` o CSV en repo) con columnas:

`id_caso | descripción | archivo_auditoría | sección_o_línea | test_automatizado (path::test_name)`

CI falla si fila sin test y capability marcada «obligatoria».

---

## 9. Concurrencia `codmov`

- Test con dos threads/procesos que intentan posting simultáneo: uno debe esperar o fallar controladamente; **sin** duplicar `CodigoMovimiento`. *Riesgo pendiente* tuning locks.

---

## 10. OCR

- **Sin** llamar OCR real en CI por defecto: fixture de JSON con salida OCR fija. *Decisión nueva.*
- Test opcional «smoke» con API real en pipeline nocturno.

---

## 11. Cumplimiento proyecto Synap

- Comandos `manage.py test` en contenedor `Synap_app` cuando se integre al monorepo ([.cursorrules](../.cursorrules)).

---

## 12. Métricas de calidad

- Cobertura mínima en módulo `factura_compra_posting` ≥ umbral acordado (ej. 85% líneas).
- Cero tests «skipped» para casos CA-* del PRD sin justificación en ticket.
