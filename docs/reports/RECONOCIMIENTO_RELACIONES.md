# Reconocimiento de Relaciones en el Builder Visual

## Resumen Ejecutivo

El sistema de reconocimiento de relaciones en el Builder Visual utiliza **tres mecanismos complementarios** para identificar posibles JOINs entre tablas:

1. **Foreign Keys Explícitas** (confianza 1.0)
2. **Heurísticas de Nombres** (confianza 0.5-0.6)
3. **Relaciones Aprendidas** (confianza variable según uso)

## ¿Por qué aparece "No hay tablas relacionadas disponibles"?

Este mensaje aparece cuando el sistema **no encuentra ninguna relación** para la tabla seleccionada (`cliente` en tu caso) mediante ninguno de los tres mecanismos. Esto puede ocurrir cuando:

- ❌ **No hay Foreign Keys explícitas** definidas en la base de datos
- ❌ **Las heurísticas no encuentran coincidencias** (nombres de campos no siguen patrones reconocidos)
- ❌ **No hay relaciones aprendidas** (nunca se ha usado un JOIN desde esa tabla)

### Solución

En estos casos, el sistema ofrece el **"Modo Avanzado"** donde puedes:
- Seleccionar manualmente cualquier tabla de la base de datos
- Definir manualmente la condición `ON` del JOIN
- El sistema aprenderá esta relación para futuras sugerencias

---

## 1. Reconocimiento de la Estructura/Schema de la DB

### ¿Se lee en tiempo real?

**Sí, pero con cacheo inteligente:**

El sistema utiliza `SemanticService` que:

1. **Lee metadata en tiempo real** desde `INFORMATION_SCHEMA` de MySQL:
   - Tablas disponibles (`TABLES`)
   - Columnas y tipos (`COLUMNS`)
   - Claves primarias (`KEY_COLUMN_USAGE` con `CONSTRAINT_NAME = 'PRIMARY'`)
   - **Claves foráneas** (`KEY_COLUMN_USAGE` con `REFERENCED_TABLE_NAME IS NOT NULL`)

2. **Cachea resultados** en memoria por 1 hora (`_cache_ttl = 3600`) para mejorar rendimiento:
   ```python
   cache_key = f"relationships_{datasource_name}_{base_empresa or 'default'}"
   ```

3. **Limpia el cache** automáticamente cuando detecta cambios o manualmente con `clear_cache()`

### Código relevante:

```python
# reports/services/semantic_service.py

@classmethod
def get_relationships(cls, datasource_name: str, base_empresa: Optional[str] = None, empresa: Optional[Any] = None) -> List[SemanticRelationship]:
    # 1. Buscar Foreign Keys explícitas
    cursor.execute("""
        SELECT 
            COLUMN_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = %s
        AND REFERENCED_TABLE_NAME IS NOT NULL
    """, (base_empresa, datasource_name))
    
    # 2. Si no hay FKs, usar heurísticas
    if len(relationships) == 0:
        relationships.extend(cls._infer_relationships_heuristic(...))
    
    # 3. Integrar relaciones aprendidas
    learned_rels = RelationshipLearningService.get_learned_relationships(...)
```

---

## 2. Inferencia de Relaciones por Heurísticas

### ¿Se infieren relaciones según campos con id hacia otras tablas?

**Sí, absolutamente.** El sistema implementa dos heurísticas principales:

### Heurística 1: Campos que terminan en `_id`

```python
# Ejemplo: campo "distrito_id" → busca tabla "distrito" o "distritos"
if col_name.lower().endswith('_id'):
    potential_table = col_name[:-3]  # Quitar "_id"
    # Busca tabla que coincida (singular o plural)
    for table in available_tables:
        if table.lower() == potential_table or table.lower() == potential_table + 's':
            # Verifica que la tabla tenga un campo "id" o "id_*"
            # Si existe, crea relación con confidence=0.6
```

**Ejemplo práctico:**
- Campo: `cliente.distrito_id`
- Busca tabla: `distrito` o `distritos`
- Si encuentra tabla con campo `id` o `id_distrito`:
  - ✅ Crea relación: `cliente.distrito_id` → `distrito.id`
  - Confidence: **0.6** (heurística)

### Heurística 2: Campos que empiezan con `Cod*` o `cod*`

```python
# Ejemplo: campo "CodSucursal" → busca tabla "sucursales"
elif col_name.lower().startswith('cod'):
    potential_table = col_name[3:].lower()  # Quitar "cod"
    # Busca tabla que contenga o sea similar al nombre
    for table in available_tables:
        if potential_table in table.lower() or table.lower() in potential_table:
            # Verifica campo "id" o "id_*" en tabla destino
            # Si existe, crea relación con confidence=0.5
```

**Ejemplo práctico:**
- Campo: `cuentacliente.CodSucursal`
- Busca tabla: `sucursales` (contiene "sucursal")
- Si encuentra tabla con campo `id_sucursal`:
  - ✅ Crea relación: `cuentacliente.CodSucursal` → `sucursales.id_sucursal`
  - Confidence: **0.5** (heurística, menor confianza)

### Niveles de Confianza

| Fuente | Confidence | Badge | Descripción |
|--------|-----------|-------|-------------|
| Foreign Key explícita | 1.0 | "Detectado" | Relación definida en el esquema de la DB |
| Heurística `_id` | 0.6 | "Sugerido" | Campo termina en `_id`, tabla encontrada |
| Heurística `Cod*` | 0.5 | "Sugerido" | Campo empieza con `cod*`, tabla encontrada |
| Relación aprendida (alta) | 0.8-0.9 | "Recomendado" | Usada exitosamente muchas veces |
| Relación aprendida (media) | 0.6-0.7 | "Sugerido" | Usada algunas veces |

---

## 3. Relaciones Aprendidas (Machine Learning Básico)

El sistema también **aprende de los JOINs que los usuarios crean**:

### Proceso de Aprendizaje:

1. **Cuando un usuario guarda un reporte con JOINs:**
   - El sistema registra cada JOIN usado en `LearnedRelationship`
   - Incrementa contador de usos exitosos

2. **Cuando un usuario hace preview exitoso:**
   - Incrementa `success_count`
   - Aumenta `confidence` gradualmente

3. **Cuando un preview falla:**
   - Incrementa `failure_count`
   - Disminuye `confidence`

4. **En futuras búsquedas:**
   - Las relaciones aprendidas se combinan con FKs y heurísticas
   - Se priorizan según `confidence` y `usage_count`
   - Reciben badge "Recomendado" si tienen alta confianza

### Código relevante:

```python
# reports/api_views.py

def _learn_relationships_from_config(cls, empresa, config, base_table, success=True):
    """Extrae y registra relaciones de JOINs desde la configuración."""
    joins = config.get("joins", [])
    for join in joins:
        RelationshipLearningService.record_join_usage(
            empresa=empresa,
            from_table=source_table,
            from_column=from_field,
            to_table=target_table,
            to_column=to_field,
            success=success
        )
```

---

## Flujo Completo de Reconocimiento

```
Usuario selecciona tabla "cliente"
         ↓
SemanticService.get_relationships("cliente")
         ↓
┌─────────────────────────────────────────┐
│ 1. Buscar Foreign Keys explícitas       │
│    → INFORMATION_SCHEMA.KEY_COLUMN_USAGE│
│    → confidence=1.0, source="foreign_key"│
└─────────────────────────────────────────┘
         ↓ (si no hay FKs)
┌─────────────────────────────────────────┐
│ 2. Aplicar heurísticas                  │
│    → Buscar campos *_id                 │
│    → Buscar campos Cod*                 │
│    → confidence=0.5-0.6, source="heuristic"│
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ 3. Integrar relaciones aprendidas       │
│    → LearnedRelationship.objects.filter │
│    → confidence variable según uso     │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ 4. Merge y ranking                      │
│    → RelationshipLearningService.merge  │
│    → Ordenar por confidence desc       │
│    → Asignar badges (Recomendado/Detectado/Sugerido)│
└─────────────────────────────────────────┘
         ↓
Frontend recibe lista de candidatas
         ↓
Si lista vacía → Mostrar "No hay tablas relacionadas disponibles"
```

---

## Recomendaciones para Mejorar el Reconocimiento

### Para la tabla `cliente`:

1. **Verificar Foreign Keys:**
   ```sql
   SELECT 
       COLUMN_NAME,
       REFERENCED_TABLE_NAME,
       REFERENCED_COLUMN_NAME
   FROM information_schema.KEY_COLUMN_USAGE
   WHERE TABLE_SCHEMA = 'tu_base'
   AND TABLE_NAME = 'cliente'
   AND REFERENCED_TABLE_NAME IS NOT NULL;
   ```

2. **Verificar campos con patrones reconocidos:**
   ```sql
   SELECT COLUMN_NAME
   FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = 'tu_base'
   AND TABLE_NAME = 'cliente'
   AND (
       COLUMN_NAME LIKE '%_id'
       OR COLUMN_NAME LIKE 'cod%'
       OR COLUMN_NAME LIKE 'Cod%'
   );
   ```

3. **Crear relaciones manualmente en Modo Avanzado:**
   - El sistema aprenderá estas relaciones
   - En futuras sesiones aparecerán como sugerencias

4. **Agregar Foreign Keys en la base de datos:**
   - Mejora la confiabilidad del sistema
   - Permite relaciones con confidence=1.0

---

## Archivos Clave

- `reports/services/semantic_service.py`: Lógica principal de reconocimiento
- `reports/services/relationship_learning.py`: Aprendizaje de relaciones
- `reports/models.py`: Modelo `LearnedRelationship`
- `reports/api_views.py`: Endpoint `BuilderJoinsCandidatesAPIView`

---

## Conclusión

El sistema es **robusto y multi-capa**, pero depende de:
- ✅ Estructura de la base de datos (Foreign Keys)
- ✅ Convenciones de nombres (heurísticas)
- ✅ Uso previo (aprendizaje)

Si ninguna de estas condiciones se cumple para una tabla específica, el sistema correctamente indica que no hay relaciones disponibles y ofrece el Modo Avanzado como alternativa segura.





