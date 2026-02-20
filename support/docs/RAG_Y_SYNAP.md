# RAG y conocimiento desde Synap

Support usa una base de conocimiento (RAG) para que el copiloto pueda responder con contexto de producto y de Synap/AdministraNET.

## Configuración automática ya aplicada

- **Synap**: Expone `GET /core/api/support/conocimiento/` (devuelve ítems de conocimiento funcional).
- **Support (backend)**:
  - `support/backend/.env`: `SUPPORT_SYNAP_API_URL=http://localhost:8000` (cuando backend y Synap corren en el mismo host).
  - `support/docker/.env`: `SUPPORT_SYNAP_API_URL=http://host.docker.internal:8000` (cuando Support corre en Docker y Synap en el host).
- **Test automatizado**: `apps.api.tests_smoke.SyncRagFromSynapSmokeTests` — ejecutar con `python manage.py test apps.api.tests_smoke.SyncRagFromSynapSmokeTests` (o desde el contenedor: `docker exec support_backend python manage.py test apps.api.tests_smoke.SyncRagFromSynapSmokeTests`).
- **Comando de carga**: `python manage.py sync_rag_from_synap [--company-id ID]` (o desde contenedor: `docker exec support_backend python manage.py sync_rag_from_synap`). Requiere Synap levantado y alcanzable desde donde se ejecuta el comando.

## Activar RAG

1. **Configurar embeddings**  
   En `.env` del backend Support definir `OPENAI_API_KEY` (puede ser la misma que en Configuración → IA). Sin esta variable la búsqueda vectorial no estará disponible (sí se puede usar búsqueda textual con `?fallback=text` en la API de búsqueda).

2. **Configuración en la UI**  
   En **Configuración** → **RAG / Conocimiento**: activar el interruptor "RAG activo", ajustar Top K si se desea y guardar.

3. **Cargar conocimiento desde Synap**  
   Pulsar **"Cargar desde Synap"**. Support llamará a Synap en `GET /core/api/support/conocimiento/`, obtendrá la lista de ítems (texto, source_id, metadata) e ingesta en la base de conocimiento con `source_type=synap`. Los embeddings se generan en segundo plano (Celery).

## Endpoint en Synap

Synap expone:

- **GET** `/core/api/support/conocimiento/`  
  Devuelve `{ "items": [ { "text", "source_id", "metadata" } ] }`.

**Origen del contenido:** Synap lee la carpeta `docs/` desde el filesystem en cada petición (sin caché). Recorre recursivamente todos los `.md` bajo `docs/`, excepto que el contenido bajo **`docs/administranet_vb6/`** se etiqueta como sistema **AdministraNET (VB6)**; el resto se etiqueta como **Synap**. Cada archivo se divide en fragmentos (chunking por encabezados `##` y, si una sección supera el límite, por longitud). Cada ítem incluye `metadata.sistema` (`"synap"` o `"administranet"`) y `metadata.file` (ruta relativa). Así, cada vez que en Support se pulsa **"Cargar desde Synap"** se obtiene el estado actual de la documentación.

**Carpeta AdministraNET:** Los `.md` que describen solo AdministraNET (VB6) —procedimientos, tablas VB6, menú Archivo, etc.— deben estar en **`docs/administranet_vb6/`** para que el RAG los etiquete como `administranet` y el copiloto pueda filtrar por ese sistema. Ver `docs/administranet_vb6/README.md` en el repo Synap.

En producción conviene proteger este endpoint (p. ej. restringir por IP del servicio Support o validar JWT con un secreto compartido).

## Flujo en Support

1. **Sync**  
   `POST /api/knowledge/sync-from-synap/` (body opcional: `{ "company_id": number | null }`). Support usa `SynapClient.get_conocimiento()` y luego `KnowledgeIngestionService.create_or_update_chunks(..., source_type="synap")`. Los ítems ya traen `metadata.sistema` desde Synap y se conservan en cada chunk.

2. **Copiloto (solo RAG)**  
   El copiloto responde **únicamente** con información del RAG: no inventa datos ni alucina. Si RAG está activo y hay embeddings, se hace una búsqueda por similitud; los fragmentos relevantes (top_k) se inyectan en el prompt como "Contexto de la base de conocimiento". Si no hay contexto RAG (RAG inactivo, sin embeddings o sin chunks relevantes), no se llama al LLM: se devuelve un mensaje fijo de derivación y el caso pasa a estado **Derivado a humano** para que lo atienda un agente.

3. **Filtro por sistema (Synap vs AdministraNET)**  
   El copiloto puede restringir la búsqueda RAG a un solo sistema. En el chat del copiloto (detalle de caso y en **Configuración → IA → Probar LLM**) hay un selector **"Pregunta sobre: Synap | AdministraNET (VB6) | Ambos"**. Si se elige Synap o AdministraNET, Support filtra los chunks con `metadata.sistema` igual al valor elegido, de modo que las respuestas se basen solo en la documentación de ese sistema. La API de copiloto acepta en el body un campo opcional `sistema` (`"synap"` o `"administranet"`). La API de búsqueda de conocimiento acepta el query param opcional `sistema` para pruebas.

## Dónde ver la información ingestada

- **UI de Support (recomendado)**  
  En **Configuración** → **RAG / Conocimiento** abrí el acordeón **"Conocimientos cargados"**. Ahí se listan los fragmentos (chunks) con tipo de fuente, sistema (Synap/AdministraNET), vista previa del texto, si tienen embedding y fecha. Podés filtrar por fuente (Synap, nota humana, caso resuelto, etc.) y paginar.

- **Django Admin**  
  En **`/admin/`** → **Knowledge** → **Chunks conocimiento** podés ver todos los fragmentos, filtrar por tipo fuente y empresa, y buscar por texto.

- **API de búsqueda (debug)**  
  **`GET /api/knowledge/search?q=ajuste+stock&sistema=synap`** (requiere autenticación y rol admin). La respuesta incluye los chunks que el copiloto usaría como contexto para esa consulta.

## Variables

- **Support (backend)**  
  - `OPENAI_API_KEY`: para generar embeddings (ingesta y búsqueda).  
  - `SUPPORT_SYNAP_API_URL`, `SUPPORT_SYNAP_JWT_SECRET`: para que Support pueda llamar a Synap y traer el conocimiento.

- **Synap**  
  No requiere variables adicionales para el endpoint de conocimiento; la protección del endpoint es opcional (VPN, JWT, IP).
