# Aprendizaje desde el chat y fine-tuning (módulo IA)

## Objetivo

Acumular **ejemplos supervisados** a partir del uso real del asistente (turnos usuario/asistente), con **revisión humana** y **exportación JSONL** para entrenar o afinar modelos en el proveedor (p. ej. fine-tuning de chat en OpenAI). Esto complementa la **memoria episódica** (`AgentMemoryItem`) y el **transcript** del hilo: aquí el foco es un **dataset versionable** para mejorar el comportamiento del modelo, no solo recordar hechos en la conversación.

## Qué no hace Synap automáticamente

- **No** lanza trabajos de fine-tuning en la API del proveedor desde la aplicación (coste, políticas, evaluación offline).
- **No** sustituye el modelo base solo por acumular ejemplos: hace falta un proceso externo (CLI del proveedor o pipeline propio) y, en general, **promoción** del nuevo identificador de modelo en la configuración del agente.

## Flujo en Synap

1. **Captura (opt-in):** si el agente tiene en `config` la clave `learning` con `capture_successful_turns: true`, tras cada turno que termina en estado de ejecución **éxito** (y opcionalmente **parcial** si se configura) se crea un `AgentLearningExample` en estado **pendiente**, con copia del **system prompt** y del par usuario/asistente en `messages_payload` (formato lista `{role, content}`).
2. **Respuesta API:** el endpoint `POST .../conversations/<uuid>/messages/` devuelve `learning_example_id` cuando se creó un ejemplo (o `null`).
3. **Revisión:** `POST .../conversations/<uuid>/learning-examples/<id>/review/` con cuerpo:
   - `action`: `approve` | `reject` | `mark_exported`
   - `notes` (opcional)
   - `corrected_assistant_text` (opcional): si va con `approve`, reemplaza la respuesta del asistente en el payload exportable y marca el origen como corrección de usuario.
4. **Exportación:** comando de gestión que escribe un **archivo JSONL** (una línea JSON por ejemplo), clave raíz `messages`, alineado al formato de fine-tuning tipo chat de proveedores compatibles con OpenAI.

## Configuración del agente (`AgentDefinition.config`)

Ejemplo mínimo para activar la captura:

```json
{
  "learning": {
    "capture_successful_turns": true,
    "include_partial_executions": false
  }
}
```

- **`capture_successful_turns`:** debe ser `true` para registrar ejemplos (por defecto en Synap está **desactivado** por privacidad y control de datos).
- **`include_partial_executions`:** si es `true`, también se capturan turnos cuya ejecución quedó en estado **parcial** (p. ej. degradación por error de proveedor).

## Comando de exportación

Desde el contenedor de la app:

```bash
docker exec Synap_app python manage.py export_ia_learning_jsonl \
  --agent-slug asistente-reportes \
  --status approved \
  --output /tmp/asistente_reportes_aprobados.jsonl
```

Opciones útiles:

- `--mark-exported`: tras escribir el archivo, pasa los ejemplos exportados a estado **exportado** para no duplicarlos en el siguiente lote.
- `--limit N`: máximo de filas.
- `--status`: por defecto `approved`; se puede exportar también `pending` en entornos de prueba (no recomendado para entrenamiento sin revisión).

## Uso del dataset en el proveedor

1. Subir el `.jsonl` según la documentación del proveedor (fine-tuning de chat).
2. Al obtener el **modelo afinado** (identificador string), asignarlo al agente como **`default_model_name`** (o el campo que use el selector de modelos) en la UI de Synap, tras pruebas en un entorno controlado.

## Privacidad y cumplimiento

- La captura puede incluir **datos de negocio** presentes en preguntas y respuestas. Mantener la captura **desactivada** hasta política explícita por empresa.
- Revisar y **rechazar** ejemplos sensibles; usar exportación solo sobre estados **approved** en producción.

## Referencias de código

- Modelo: `ia.models.AgentLearningExample`
- Captura: `ia.services.learning_capture_service.LearningCaptureService`
- Export JSONL: `ia.services.learning_capture_service.LearningExportService`, comando `export_ia_learning_jsonl`
- Orquestador: `ia.services.orchestrator.AgentOrchestrator` (creación del ejemplo tras el turno)
- API: `ia.api_views.AgentConversationMessageAPIView`, `AgentLearningExampleReviewAPIView`
