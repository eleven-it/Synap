# Reglas de Arquitectura y Modelado en Synap

## Regla de Modelos Troncales y Estructura Modular en Synap

### 1. Centralización en el módulo `core`
- Todos los modelos, definiciones y utilidades que sean **troncales, transversales o fundamentales** para el funcionamiento del sistema (por ejemplo: Empresa, Usuario, Rol, Permiso, Sucursal, Configuración global, etc.) **deben ser definidos exclusivamente en el módulo `core`**.
- El módulo `core` es el corazón de Synap, equivalente al módulo `base` en Odoo, y su propósito es centralizar la lógica, modelos y utilidades esenciales que serán reutilizados o referenciados por el resto de las aplicaciones del sistema.

### 2. Relaciones y dependencias
- **Ningún otro módulo o app** (por ejemplo: inventario, ingresos, egresos, integraciones, etc.) debe redefinir, duplicar o extender directamente estos modelos troncales fuera de `core`.
- Todas las apps adicionales deben **referenciar los modelos troncales de `core` mediante relaciones** (ForeignKey, ManyToMany, OneToOne, etc.) y nunca crear versiones paralelas o independientes de los mismos conceptos.

### 3. Evolución y extensibilidad
- Si en el futuro se requiere agregar atributos, métodos o lógica específica a un modelo troncal, **debe hacerse mediante herencia, mixins o extensiones limpias**, pero siempre manteniendo la definición base en `core`.
- Cualquier funcionalidad o utilidad que pueda ser útil para más de un módulo, o que afecte a la estructura general del sistema, **debe evaluarse para ser incluida en `core`**.

### 4. Propósito
- Esta regla garantiza la **consistencia, mantenibilidad y escalabilidad** del sistema Synap, evitando duplicidad de lógica y facilitando la evolución hacia un sistema multiempresa, multi-tenant y modular.

---

**Resumen corto para documentación:**

> Todos los modelos y utilidades troncales o transversales deben definirse exclusivamente en el módulo `core`, que actúa como base del sistema. Ningún otro módulo debe redefinir estos modelos, sino referenciarlos mediante relaciones. Cualquier extensión o lógica global debe centralizarse en `core` para asegurar coherencia y escalabilidad. 