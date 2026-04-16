# Arquitectura del módulo IA en Synap

## Visión de producto

Los agentes de Synap no deben concebirse como chatbots encima de formularios ni como un “chat SQL” incrustado en un módulo tradicional.

Deben ser **asistentes personales persistentes**, con memoria acumulativa y contexto operativo por cliente, capaces de:

- conversar en lenguaje natural;
- recordar definiciones, preferencias y contexto histórico;
- aprender patrones útiles del negocio con el tiempo;
- ejecutar herramientas de forma segura;
- y responder con continuidad entre sesiones, dispositivos y canales.

Ese acumulado de contexto y memoria es parte central del valor del producto: cada interacción útil vuelve al agente más preciso, más adaptado al negocio del cliente y más costoso de reemplazar.

## Objetivo

Definir la arquitectura base del nuevo módulo `ia` de Synap para alojar un ecosistema de asistentes IA multiagente, comenzando por el **Asistente de Reportes**, con estas condiciones:

- memoria persistente por cliente, por agente y por usuario cuando aplique;
- orquestación preparada desde el día uno para incorporar nuevos agentes;
- selección configurable de proveedor y modelo por agente y por tipo de tarea;
- experiencia principal conversacional, `PWA Mobile First + Desktop`;
- seguridad, permisos y trazabilidad gobernados por Synap.

## Tesis arquitectónica

El módulo `ia` debe estar pensado como una **capa asistencial transversal** y no como una colección de pantallas tradicionales.

La interfaz principal del producto debe ser la conversación.
Los formularios, filtros, exports, tarjetas, timelines o paneles quedan como superficies de apoyo, no como requisito para operar.

En otras palabras:

- el usuario habla;
- el agente entiende;
- consulta memoria;
- ejecuta herramientas;
- decide si necesita aclarar;
- responde con contexto acumulado;
- y deja memoria útil para la próxima interacción.

## Principios de diseño

1. **Asistente antes que módulo.** La experiencia primaria es conversacional y contextual.
2. **Memoria persistente como activo.** El sistema debe recordar información útil del negocio con gobierno y trazabilidad.
3. **Seguridad primero.** Ningún agente puede saltar permisos, exponer secretos ni ejecutar acciones fuera de su alcance.
4. **Los LLM no gobiernan la seguridad.** El modelo interpreta y redacta; Synap valida, filtra y ejecuta.
5. **Proveedor desacoplado.** Cada agente puede usar OpenAI, Claude, modelos OpenAI-compatible u otros futuros.
6. **Orquestación desde el día uno.** El núcleo debe quedar listo para agregar agentes y handoffs sin rehacer la base.
7. **Contratos estructurados.** La salida accionable del modelo debe ser validable.
8. **PWA Mobile First + Desktop.** La arquitectura de experiencia debe priorizar móvil sin degradar escritorio.
9. **Reutilización del dominio existente.** Los agentes se montan sobre capacidades ya gobernadas de Synap.

## Experiencia de producto

### Superficie principal

El módulo `ia` debe exponerse como una bandeja de asistentes, no como un menú de pantallas rígidas.

El usuario debe poder:

- abrir un asistente;
- conversar desde móvil o desktop;
- retomar conversaciones previas;
- ver memoria relevante;
- aprobar o revisar acciones sugeridas;
- recibir respuestas con contexto acumulado.

### PWA Mobile First + Desktop

La interfaz del módulo `ia` debe diseñarse desde origen como `PWA Mobile First + Desktop`.

Implicancias:

- diseño conversacional primero para móvil;
- sesiones persistentes entre app instalada y navegador;
- navegación mínima y centrada en asistente activo;
- handoff fluido entre móvil y escritorio;
- soporte de respuestas streaming;
- acceso rápido a memoria, acciones sugeridas, adjuntos y resultados estructurados;
- componentes de apoyo reutilizables en mobile y desktop.

### Sin menús obligatorios, sin formularios obligatorios

El módulo puede reutilizar información y capacidades de otros dominios de Synap, pero la interacción no debe exigir al usuario recorrer módulos clásicos, pestañas o formularios salvo cuando una tarea específica lo requiera.

La regla debe ser:

- conversación primero;
- UI estructurada cuando agrega claridad, seguridad o confirmación;
- nunca al revés.

## Alcance inicial

La primera iteración debe cubrir:

- un módulo transversal `ia`;
- un `Agent Orchestrator` ya preparado para multiagente;
- un agente inicial `Asistente de Reportes`;
- memoria persistente básica desde el día uno;
- integración segura con `reports`;
- soporte para OpenAI, Claude y proveedores OpenAI-compatible;
- trazabilidad completa de conversaciones, herramientas, memoria y consultas ejecutadas.

## Capacidades troncales del módulo

El núcleo del módulo `ia` debe soportar, desde la primera versión, cinco capacidades transversales:

1. conversación;
2. memoria;
3. orquestación;
4. herramientas;
5. gobierno y seguridad.

## Memoria persistente

### Objetivo

Cada agente debe poder construir y consultar memoria útil con el tiempo.

La memoria no debe ser un simple historial bruto de chat, sino una capa gobernada de conocimiento acumulado con:

- procedencia;
- vigencia;
- nivel de confianza;
- sensibilidad;
- alcance.

### Tipos de memoria sugeridos

#### 1. Memoria de perfil

Datos relativamente estables sobre el cliente, empresa, usuario o equipo:

- nombre comercial;
- sucursales;
- definiciones propias del negocio;
- KPIs prioritarios;
- preferencias de visualización;
- términos internos.

#### 2. Memoria episódica

Hechos o interacciones puntuales relevantes:

- preguntas frecuentes recientes;
- decisiones tomadas;
- aclaraciones de métricas;
- follow-ups pendientes;
- incidentes operativos relevantes.

#### 3. Memoria semántica

Conocimiento consolidado del negocio:

- definiciones de métricas por cliente;
- equivalencias de términos;
- relaciones entre áreas;
- interpretaciones aprobadas;
- patrones recurrentes útiles.

#### 4. Memoria de trabajo

Contexto temporal de la conversación activa:

- tema actual;
- entidades mencionadas;
- filtros recientes;
- subtareas abiertas;
- herramientas ya ejecutadas.

### Reglas de memoria

- la memoria debe ser persistente pero gobernada;
- toda escritura de memoria debe tener procedencia;
- el LLM no debe escribir memoria definitiva sin validación o política explícita;
- debe existir expiración o revisión para memorias temporales;
- debe existir partición por tenant;
- debe poder consultarse y, cuando la política lo requiera, corregirse o invalidarse.

## Orquestación multiagente

### Decisión estructural

Aunque el primer agente sea el de reportes, el `Agent Orchestrator` debe nacer ya preparado para alojar múltiples agentes y handoffs.

### Objetivo del orquestador

Resolver qué agente actúa, qué memoria consulta, qué herramientas puede usar, qué modelo conviene para la tarea y cómo se devuelve la respuesta final con trazabilidad.

### Responsabilidades del `AgentOrchestrator`

1. recibir la interacción;
2. obtener contexto del usuario;
3. validar acceso al módulo `ia`;
4. seleccionar agente activo o sugerir handoff;
5. recuperar memoria relevante;
6. decidir proveedor/modelo por tarea;
7. entregar herramientas permitidas;
8. ejecutar el loop de herramientas;
9. consolidar memoria nueva si corresponde;
10. validar la respuesta final;
11. registrar trazabilidad.

### Tipos de handoff que debe soportar

- `router -> agente especializado`
- `agente -> subagente de herramienta`
- `agente -> agente humano o revisión manual`
- `agente -> fallback de proveedor/modelo`

### Agentes futuros previstos

- reportes;
- ventas;
- compras;
- logística;
- stock;
- caja / TPV;
- SIA;
- administrativo / backoffice.

## Estructura propuesta

```text
ia/
  agents/
    reportes/
      AGENT.md
      SOUL.md
      TOOLS.md
      SCHEMA_REPORT_QUERY_SPEC.json
    ventas/
    compras/
    logistica/
    stock/
  providers/
    base.py
    openai_provider.py
    anthropic_provider.py
    openai_compatible_provider.py
    local_provider.py
  services/
    orchestrator.py
    agent_registry.py
    routing_service.py
    memory_service.py
    memory_index_service.py
    memory_consolidation_service.py
    policy_gate.py
    model_selection_service.py
    tool_registry.py
    trace_service.py
    response_formatter.py
    quota_service.py
    date_range_service.py
  tools/
    reportes.py
    memoria.py
    seguridad.py
  pwa/
    manifest.py
    conversation_state.py
  api_views.py
  urls.py
  models.py
```

## Componentes principales

### 1. `AgentRegistry`

Registro de agentes disponibles y su configuración:

- slug;
- dominio;
- capacidades;
- herramientas permitidas;
- política de memoria;
- configuración de modelos;
- política de handoff;
- cuotas y límites.

### 2. `AgentOrchestrator`

Núcleo del módulo. Coordina conversación, memoria, modelos y herramientas.

No debe conocer reglas de negocio profundas de cada agente. Solo debe orquestar.

### 3. `RoutingService`

Determina:

- si la consulta la toma el agente activo;
- si requiere otro agente;
- si conviene resolver una subtarea con otro modelo;
- si debe pedirse aclaración antes de continuar.

### 4. `MemoryService`

Gestiona lectura y escritura de memoria persistente.

Debe soportar:

- recuperación por relevancia;
- memoria por tenant;
- memoria por agente;
- memoria por usuario cuando aplique;
- TTL o vigencia;
- invalidación;
- proveniencia.

### 5. `MemoryConsolidationService`

No toda interacción debe guardar memoria.

Este servicio decide qué se conserva, con qué formato y con qué nivel de confianza:

- preferencia estable;
- definición de negocio;
- follow-up;
- hecho operativo;
- contexto temporal.

### 6. `ModelSelectionService`

Selecciona proveedor y modelo por tarea, no solo por agente.

Debe poder decidir entre:

- modelo principal del agente;
- modelo de tool use;
- modelo de memoria;
- modelo económico para resumen o clasificación;
- fallback aprobado.

### 7. `PolicyGate`

Aplica endurecimiento antes de invocar proveedor, memoria o herramientas.

Debe validar:

- usuario autenticado;
- empresa y sucursal activas;
- permisos por agente;
- límites de uso;
- sensibilidad del dato;
- políticas de memoria;
- estado operativo del proveedor.

### 8. `ToolRegistry`

Expone al agente solo herramientas aprobadas y con contrato estricto.

### 9. `TraceService`

Registra trazabilidad de:

- conversación;
- decisiones de routing;
- consultas a memoria;
- escrituras de memoria;
- herramientas;
- proveedor/modelo;
- costos y tiempos.

## Configuración de modelos por agente

### Requisito

Cada agente debe poder configurar explícitamente:

- proveedor preferido;
- modelo principal;
- modelo para tool use;
- modelo para consolidación de memoria;
- modelo para respuestas rápidas o económicas;
- fallback chain;
- temperatura;
- nivel de razonamiento;
- límites de tokens;
- soporte de structured outputs;
- soporte de vision si fuera necesario.

### Fuente de configuración

La configuración de proveedores LLM, credenciales y modelos por agente debe gestionarse por **UI administrativa del módulo `ia`**.

No debe quedar hardcodeada en el código de cada agente ni depender exclusivamente de variables de entorno por agente.

Las variables de entorno pueden seguir existiendo para casos globales o contingencia, pero la operación normal del producto debe permitir:

- cargar credenciales del proveedor por interfaz;
- declarar modelos disponibles por proveedor;
- elegir desde UI qué modelo usa cada agente para cada tipo de tarea;
- ajustar fallback sin desplegar código.

### Configuración sugerida

Campos recomendados en `AgentDefinition` o config equivalente:

- `provider_kind`
- `default_model_name`
- `tool_use_model_name`
- `memory_write_model_name`
- `fast_model_name`
- `fallback_provider_kind`
- `fallback_model_name`
- `reasoning_profile`
- `max_input_tokens`
- `max_output_tokens`
- `supports_structured_output`
- `supports_parallel_tool_calls`
- `supports_streaming`
- `supports_vision`

### Regla importante

La arquitectura no debe asumir que un agente usa un único modelo para todo.

Un mismo agente puede necesitar:

- un modelo fuerte para interpretar;
- uno rápido para clasificación;
- uno más económico para resumen;
- uno local para tareas auxiliares.

## Proveedores soportados

### OpenAI

Adecuado para:

- salidas estructuradas;
- tool calling robusto;
- tareas de razonamiento;
- orquestación con contratos JSON estrictos.

### Anthropic / Claude

Adecuado para:

- síntesis ejecutiva;
- tareas conversacionales largas;
- desambiguación cuidadosa;
- tool use con buena calidad de redacción final.

### OpenAI-compatible

Debe permitir integrar:

- Ollama;
- vLLM;
- LM Studio;
- gateways internos;
- proveedores futuros compatibles.

### Modelos locales o SMLs

Recomendados para:

- clasificación de intención;
- detección de ambigüedad;
- tagging de memoria;
- normalización simple;
- heurísticas de bajo costo.

No deben usarse para decisiones de permisos ni para responder sin validación.

## Recomendación de modelo según tarea

La recomendación debe expresarse como política configurable, no como hardcode rígido.

### Tareas con razonamiento y herramientas

Usar el mejor modelo habilitado para tool use y structured output del proveedor elegido.

Casos:

- consultas complejas;
- planificación de pasos;
- interpretación ambigua;
- decisiones de herramienta.

### Tareas de memoria

#### Recuperación

Puede resolverse con embeddings, búsqueda semántica y re-ranking ligero, sin consumir siempre el mejor LLM.

#### Consolidación

Usar un modelo confiable pero no necesariamente el más caro, porque debe:

- resumir con precisión;
- clasificar tipo de memoria;
- asignar confianza;
- evitar ruido o sobreescritura.

### Tareas de respuesta final

Para respuestas ejecutivas y claras, suele convenir:

- modelo principal del agente;
- o un modelo de síntesis de alta calidad si el resultado ya está validado.

### Tareas rápidas o de bajo riesgo

Usar un modelo pequeño o compatible cuando alcance para:

- clasificación;
- extracción simple;
- reetiquetado;
- sugerencias no críticas.

## Recomendación específica para el Asistente de Reportes

### Perfil del agente

El agente de reportes necesita:

- buena interpretación semántica;
- tool use ordenado;
- structured outputs confiables;
- redacción ejecutiva clara;
- disciplina para no inventar.

### Recomendación de política de modelos

- **modelo principal del agente:** uno fuerte en razonamiento + tool use;
- **modelo de consolidación de memoria:** uno intermedio y estable;
- **modelo rápido para clasificación o tagging:** uno pequeño o local;
- **fallback:** proveedor alternativo aprobado con structured outputs.

### Priorización sugerida

1. calidad de structured outputs;
2. calidad de tool use;
3. claridad de síntesis ejecutiva;
4. costo por operación;
5. latencia.

## Relación con `reports`

El Asistente de Reportes no debe consultar la base por fuera de la infraestructura existente salvo que una herramienta segura y explícita lo habilite.

La capa `reports` ya aporta:

- catálogo filtrado por permisos;
- definición declarativa de reportes;
- schemas de métricas, dimensiones y widgets;
- ejecución y caching de consultas;
- logs de ejecución.

Por eso, la estrategia correcta es:

1. consultar memoria del cliente;
2. intentar mapear la pregunta a un reporte existente;
3. resolver filtros, fechas y dimensiones;
4. ejecutar mediante `QueryRunnerService`;
5. resumir con lenguaje natural;
6. consolidar memoria útil para interacciones futuras.

## Contrato principal del agente de reportes

La salida estructurada del modelo debe mapear a un contrato canónico como `ReportQuerySpec`.

Ese contrato debe incluir:

- intención;
- reporte objetivo;
- métricas requeridas;
- dimensiones requeridas;
- filtros;
- rango temporal;
- necesidad de aclaración;
- motivo de rechazo o limitación;
- señales de memoria relevante si existieran.

El backend debe validar ese contrato antes de ejecutar cualquier herramienta.

## Flujo de extremo a extremo

```text
Usuario autenticado
  -> conversación IA
  -> PolicyGate
  -> AgentOrchestrator
  -> RoutingService
  -> MemoryService (read)
  -> ModelSelectionService
  -> LLM
  -> ToolRegistry
  -> dominio Synap (reports, etc.)
  -> ResponseFormatter
  -> MemoryConsolidationService (write candidate)
  -> TraceService
  -> respuesta final
```

## Flujo del Asistente de Reportes

1. El usuario pregunta en lenguaje natural.
2. Se recupera contexto efectivo y memoria relevante.
3. Se valida acceso al módulo `ia` y al agente `reportes`.
4. El modelo transforma la consulta en contrato estructurado.
5. Si falta información crítica, se pide aclaración mínima.
6. Si la consulta es válida, se usa catálogo, schema y herramientas de `reports`.
7. Se ejecuta la lectura segura.
8. Se responde con lenguaje ejecutivo.
9. Se consolida memoria útil, si corresponde.
10. Se guardan trazas y métricas.

## Reglas de integración con Synap

### Autenticación y sesión

- toda interacción usa el usuario autenticado de Synap;
- no se aceptan identidades ni permisos enviados por el cliente;
- timezone, empresa, sucursal y base activa se resuelven en backend.

### Multiempresa y legacy MySQL

- toda consulta debe respetar empresa, sucursal y base activa;
- los filtros de tenant deben aplicarse siempre del lado servidor;
- la memoria debe estar igualmente particionada por tenant y agente.

### Permisos

- el agente no determina permisos por sí mismo;
- las herramientas y servicios revalidan permisos;
- la memoria no puede saltar restricciones de acceso;
- debe existir degradación a respuestas agregadas cuando el detalle esté restringido.

## Seguridad por diseño

La arquitectura del módulo `ia` debe asumir que:

- el input del usuario puede intentar manipular al agente;
- la memoria puede ser objetivo de contaminación o exfiltración;
- la salida del modelo es no confiable;
- el proveedor externo no debe recibir más datos que los mínimos necesarios;
- toda herramienta puede ser abusada si no se valida;
- las respuestas deben obedecer permisos reales, no persuasión del prompt.

Las políticas concretas de endurecimiento se detallan en:

- `docs/general/SEGURIDAD_MODULO_IA_SYNAP.md`
- `ia/agents/reportes/TOOLS.md`

## Endpoints sugeridos

- `POST /api/ia/conversations/`
- `POST /api/ia/conversations/<uuid>/messages/`
- `GET /api/ia/conversations/<uuid>/`
- `GET /api/ia/agents/`
- `GET /api/ia/agents/<slug>/capabilities/`
- `GET /api/ia/agents/<slug>/memory/`
- `POST /api/ia/agents/<slug>/memory/feedback/`
- `POST /api/ia/agentes/reportes/export/`

## Modelos de datos sugeridos

- `AgentDefinition`
- `AgentPromptVersion`
- `AgentConversation`
- `AgentMessage`
- `AgentExecution`
- `AgentToolExecution`
- `AgentMemoryItem`
- `AgentMemorySource`
- `AgentMemoryFeedback`
- `LlmProviderConfig`
- `AgentQuota`
- `AgentAccessPolicy`

## Despliegue recomendado

- claves de OpenAI, Anthropic y compatibles solo en backend;
- límites de gasto por proveedor y cuotas por usuario;
- rate limiting por IP, sesión, usuario, agente y tenant;
- logs y alertas de abuso;
- separación estricta entre entornos;
- configuración para desactivar temporalmente agentes, memorias o proveedores;
- observabilidad separada por agente, herramienta y modelo.

## Fases sugeridas

### Fase 1

- Asistente de Reportes;
- conversación persistente;
- memoria básica gobernada;
- preguntas agregadas, comparativas y rankings;
- soporte multi-proveedor configurable;
- PWA base `mobile first`;
- trazabilidad completa.

### Fase 2

- router multiagente activo;
- más agentes de dominio;
- memoria semántica consolidada;
- handoffs;
- streaming;
- mejores superficies mobile y desktop.

### Fase 3

- colaboración entre agentes;
- modelos locales para tareas auxiliares;
- recomendaciones proactivas;
- observabilidad avanzada;
- políticas finas por cliente y por agente.

## Criterio rector

El módulo `ia` de Synap no debe ser un “chat con base de datos” ni un “módulo más” con una caja de texto arriba.

Debe ser una **plataforma de asistentes personales persistentes**, segura, orquestada y multiagente, donde:

- la conversación es la superficie principal;
- la memoria acumulada es parte del valor del producto;
- Synap gobierna permisos, herramientas y seguridad;
- y cada agente puede evolucionar con el modelo más adecuado para sus tareas sin romper la arquitectura común.
