# Security Rules — AI Development System

Estas reglas son obligatorias para cualquier sistema basado en agentes de IA.

---

# 1. Acceso a secretos

Los agentes nunca pueden acceder directamente a:

- API keys
- credenciales
- tokens
- secretos de infraestructura

Los secretos deben gestionarse mediante variables de entorno o gestores de secretos.

---

# 2. Permisos mínimos

Cada agente debe operar bajo el principio de:

Least Privilege.

Solo podrá usar las herramientas necesarias para su tarea.

---

# 3. Allowlist de herramientas

Los agentes solo pueden usar herramientas explícitamente autorizadas.

No se permite acceso abierto a funciones del sistema.

---

# 4. Validación de entradas

Toda entrada externa debe:

- validarse
- sanearse
- verificarse

Esto incluye:

- formularios
- prompts
- archivos
- webhooks
- APIs externas

---

# 5. Acciones críticas

Las acciones clasificadas como críticas requieren:

- aprobación humana
o
- doble validación automática

Ejemplos de acciones críticas:

- ejecución de operaciones financieras
- despliegue de infraestructura
- modificación de permisos
- borrado de datos

---

# 6. Logging obligatorio

Toda acción realizada por un agente debe registrarse incluyendo:

- agente ejecutor
- herramienta usada
- input recibido
- output generado
- timestamp

Esto permite auditoría y trazabilidad.

---

# 7. Protección contra prompt injection

Los prompts enviados al modelo deben:

- validar contexto
- eliminar instrucciones maliciosas
- limitar acceso a herramientas

El modelo nunca debe ejecutar instrucciones externas sin verificación.

---

# 8. Separación de entornos

El sistema debe diferenciar claramente entre:

- entorno de desarrollo
- entorno de pruebas
- entorno de producción

Los agentes en desarrollo no deben acceder a recursos de producción.

---

# 9. Human in the Loop

Las decisiones con impacto real deben incluir revisión humana cuando sea necesario.

---

# 10. Principio general

Los agentes no deben tener autonomía total.

Su comportamiento debe estar limitado por:

- reglas
- permisos
- auditoría
- validaciones