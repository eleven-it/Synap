# Synap Support – Plan del Módulo de Atención a Usuarios

## 1. Propósito
Synap Support es una aplicación independiente del ERP Synap, diseñada para brindar soporte a usuarios finales mediante un asistente virtual con IA, con capacidad de escalar a agentes humanos, gestionar SLA, registrar conversaciones multicanal y mantener auditoría completa.

El sistema atiende usuarios vía Telegram, WhatsApp y Email, valida su autorización, gestiona casos y ejecuta acciones sobre Synap mediante API interna.

---

## 2. Arquitectura General

### 2.1 Componentes
- Servicio **Support** (Django independiente)
- Base de datos propia (PostgreSQL)
- Object Storage (S3 compatible)
- ERP Synap (sistema externo)
- Proveedor de IA (LLM con RAG + tool-calling)

### 2.2 Integración con Synap
- Comunicación vía API interna
- Autenticación service-to-service con JWT firmado
- Permisos de lectura y escritura

---

## 3. Canales Soportados
- Telegram (telegram_user_id)
- WhatsApp (número E.164, Meta Cloud API / Twilio)
- Email (from address + subject threading)

Un usuario puede tener múltiples identidades de canal.

---

## 4. Modelo de Usuarios
- Usuario de soporte:
  - Asociado a una empresa existente en Synap
  - Idioma definido por empresa
  - Nombre persistente (confirmable)
- Alta y autorización: solo backoffice

---

## 5. Flujo de Atención

1. Mensaje entrante
2. Identificación por canal
3. Validación de autorización
4. Presentación como asistente virtual
5. Solicitud / confirmación de nombre
6. Listado de casos abiertos
7. Continuar caso o crear uno nuevo

---

## 6. Casos de Soporte

### 6.1 Numeración
Formato:
SUP-{PREFIJO_EMPRESA}-000123  
Contador por empresa, visible al usuario.

### 6.2 Estados (MVP)
- Iniciado
- En análisis IA
- Esperando respuesta del usuario
- Derivado a humano
- Asignado a agente humano
- En proceso (humano)
- Resuelto
- Cerrado
- Reabierto

### 6.3 Cierre
- IA puede cerrar con confirmación del usuario
- Cierre automático por inactividad
- Reapertura permitida

---

## 7. SLA

- Definido por empresa y tipo de caso
- Corre desde: Asignado a agente humano
- Se pausa en: Esperando respuesta del usuario

### Acciones automáticas
- Warning al 70–80%
- Vencido:
  - Escalado a gerencia
  - Notificación al usuario
  - Auditoría automática

---

## 8. IA – Diseño

### 8.1 Enfoque
- Un solo LLM
- RAG desde:
  - Código Synap
  - Casos resueltos
- Tool-calling habilitado:
  - Cambiar estado
  - Asignar agentes
  - Crear notas
  - Ejecutar acciones vía API Synap
  - Enviar notificaciones

### 8.2 Versionado
- Versionado de prompts
- Rollout controlado por empresa

### 8.3 Fallback
- Error IA → mensaje estándar + derivación automática a humano

---

## 9. Conversaciones y Adjuntos

### Conversaciones
- Log completo por mensaje
- Resúmenes automáticos por IA
- Historial inmutable
- Multicanal

### Adjuntos
- Object Storage (S3 compatible)
- URLs firmadas
- Validación de tamaño y tipo
- Retención: 12 meses

---

## 10. Backoffice

### Roles
- Administrador
- Agente humano
- Supervisor / Gerencia

### Pantallas MVP
- Dashboard
- Listado de casos
- Detalle de caso (timeline + conversación)
- Empresas (SLA, idioma)
- Usuarios y canales
- Agentes
- Métricas básicas

---

## 11. Observabilidad y Auditoría

- Logs centralizados
- Auditoría append-only
- Métricas:
  - SLA
  - Latencia
  - Uso por empresa
  - Costos IA

Retención:
- Logs: 90 días
- Auditoría: 12 meses

---

## 12. Seguridad

- Rate limiting
- Anti-spam / flood
- Validación de webhooks
- Secrets management
- Cifrado de datos sensibles
- Política estricta de no solicitar credenciales

---

## 13. Infraestructura

- Docker + Docker Compose
- Entornos: Local / Dev / Staging / Prod
- CI/CD:
  - Build Docker
  - Tests
  - Lint
  - Deploy manual aprobado

---

## 14. Backups y DR

- DB: backups diarios
- Adjuntos: versionado
- Restore manual documentado
- Retención 14–30 días

---

## 15. Roadmap Post-MVP
- Clasificación automática de casos
- Feedback humano para IA
- Panel para clientes
- Kubernetes
- Analytics avanzados
