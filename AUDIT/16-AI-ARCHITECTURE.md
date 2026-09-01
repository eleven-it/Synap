# 16 — Arquitectura de Inteligencia Artificial

**Estado:** COMPLETE (Fase 16)  
**Fecha:** 25/08/2026

---

## Componentes IA en Synap

### App `ia/` (integrada en monolito)

| Componente | Archivo | Función |
|----------|---------|---------|
| LlmGatewayService | `ia/services/llm_gateway.py` | Abstracción OpenAI/Anthropic |
| Agent services | `ia/services/` | Conversaciones, herramientas, memoria |
| Report intent | `ia/services/report_intent_refinement_service.py` | Refinamiento consultas reportes |
| Learning capture | `ia/services/learning_capture_service.py` | Captura ejemplos aprendizaje |

### Modelos (PostgreSQL)

| Modelo | Función |
|--------|---------|
| `LlmProviderConfig` | Config proveedor (API key cifrada, endpoint) |
| `AgentDefinition` | Definición agente (prompt, tools, modelo) |
| `AgentConversation` | Conversación persistente |
| `AgentMessage` | Mensajes user/assistant/system |
| `AgentExecution` | Ejecución con métricas |
| `AgentToolExecution` | Log herramientas invocadas |
| `AgentMemoryItem` | Memoria persistente por scope |
| `AgentLearningExample` | Ejemplos para fine-tuning |

### Proveedores soportados

| Provider | Protocolo | Modelos | Notas |
|----------|-----------|---------|-------|
| `openai` | REST Chat Completions | gpt-4*, gpt-5* | Activo |
| `openai_compatible` | REST (custom endpoint) | Configurable | Activo |
| `anthropic` | REST Messages API | claude-* | Activo |
| `local` | — | — | **Modelo existe; LlmGateway no lo implementa** |

**Cifrado API keys:** Fernet en `LlmProviderConfig` (PostgreSQL).

**PolicyGate:** `ia/services/policy_gate.py` — validación permisos antes de invocar herramientas LLM.

**No usa langchain/crewai** en app principal (sí en `support/`).

---

## Support RAG (proyecto separado)

| Componente | Path | Función |
|----------|------|---------|
| LangChain RAG | `support/backend/apps/knowledge/langchain_rag.py` | Retrieval augmented generation |
| pgvector | Support PostgreSQL | Embeddings storage |
| Knowledge sync | `sync_rag_from_synap` command | Importa docs Synap |
| Copilot | `support/backend/apps/api/views_cases.py` | Asistente soporte |

---

## Use cases

| Use case | Módulo | Input | Output | Permisos |
|----------|--------|-------|--------|----------|
| Chat agente | ia | Mensaje usuario + memoria | Respuesta LLM | Sesión AdministraNET |
| Refinamiento reporte | ia | Intención natural language | Query refinada | Sesión + permisos reportes |
| Tool execution | ia | Tool call del LLM | Datos MySQL/PG | **Hereda permisos agente** |
| Support copilot | support | Caso soporte + RAG | Respuesta con contexto | Auth Support |
| Learning export | ia | Conversaciones | JSONL fine-tuning | Admin |

---

## Riesgo: acceso a datos

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| IA puede invocar tools que consultan MySQL | **Alta** | Sin sandbox de datos |
| Memoria persistente cross-conversación | Media | AgentMemoryItem sin TTL claro |
| API keys en PostgreSQL | Media | LlmProviderConfig.get_api_key() |
| Support RAG accede docs completos | Media | sync_rag_from_synap |
| Sin rate limiting IA | Media | No throttle específico |
| Logging de prompts con datos sensibles | Media | AgentMessage almacena todo |

**Pregunta crítica:** ¿Puede la IA acceder a datos que el usuario no podría consultar directamente?

**Respuesta:** Si el agente tiene tools configuradas sin restricción por permiso, **sí es posible**. Los tools heredan la sesión del usuario pero no hay verificación granular documentada.

**Clasificación:** INFERIDO CON ALTA CONFIANZA — requiere auditoría tool-by-tool

---

## Almacenamiento y logging

- Conversaciones: PostgreSQL (`ia_agent*`)
- API keys: PostgreSQL cifradas en `LlmProviderConfig`
- Learning examples: PostgreSQL + export JSONL
- No hay vector DB en Synap principal (solo support pgvector)

---

*Generado por auditoría READ ONLY.*
