# Módulo Support

Documentación del **módulo Support** (aplicación de soporte al cliente con copiloto IA y base de conocimiento RAG).

## Contenido

| Documento | Descripción |
| --------- | ----------- |
| [RAG_LANGCHAIN_IMPLEMENTACION.md](RAG_LANGCHAIN_IMPLEMENTACION.md) | Refactor RAG: implementación con LangChain y PGVector (Opción A), tareas realizadas y ubicación del código. |
| [support/docs/RAG_Y_SYNAP.md](../../support/docs/RAG_Y_SYNAP.md) | Uso del RAG: configuración, activación, sync desde Synap, copiloto, filtro por sistema y variables. |

## Contexto

- **Support** es una aplicación Django (backend + frontend) que gestiona casos de soporte, integra canales (Telegram, etc.) y ofrece un **copiloto** que responde usando una base de conocimiento (RAG).
- El RAG se alimenta desde Synap (`GET /core/api/support/conocimiento/`), ingesta manual y respuestas guardadas como conocimiento.
- Desde el refactor implementado, el RAG usa **LangChain** y **PGVector** (sin tabla Django propia de chunks). Detalle en [RAG_LANGCHAIN_IMPLEMENTACION.md](RAG_LANGCHAIN_IMPLEMENTACION.md).
