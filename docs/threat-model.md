# Threat Model — AI Development System

## Objetivo
Definir riesgos potenciales y medidas de mitigación antes de implementar nuevas funcionalidades en sistemas basados en agentes de IA.

Este documento forma parte del principio **Security by Design**.

---

# 1. Activos críticos del sistema

Los siguientes activos deben considerarse sensibles:

- API keys
- Credenciales de usuario
- Bases de datos
- Integraciones externas (APIs)
- Datos personales de usuarios
- Webhooks
- Logs del sistema
- Configuraciones internas
- Infraestructura de despliegue
- Conexiones con sistemas financieros o exchanges

---

# 2. Superficies de ataque

Las principales superficies de ataque del sistema son:

- Input del usuario
- Prompts enviados al modelo
- Herramientas accesibles por agentes
- APIs externas
- Webhooks
- Archivos subidos
- Memoria o contexto de los agentes
- Integraciones con sistemas externos
- Panel de administración
- Llamadas a herramientas automáticas

---

# 3. Riesgos principales

Los riesgos que deben evaluarse incluyen:

### Prompt Injection
Un usuario manipula instrucciones del modelo para ejecutar acciones no autorizadas.

### Tool Misuse
Un agente usa herramientas para realizar acciones indebidas.

### Escalada de privilegios
Un agente obtiene acceso a recursos que no debería.

### Data Leakage
Información sensible aparece en respuestas del modelo.

### Ejecución automática peligrosa
El agente ejecuta acciones críticas sin validación.

### Dependencia excesiva del modelo
El sistema toma decisiones críticas basadas únicamente en el modelo.

### Webhook Manipulation
Un atacante envía solicitudes falsas a endpoints del sistema.

---

# 4. Mitigaciones

Las mitigaciones obligatorias del sistema incluyen:

- Validación estricta de inputs
- Uso de permisos mínimos
- Allowlist de herramientas
- Aprobación humana en acciones críticas
- Sanitización de prompts
- Separación de credenciales
- Uso de entornos sandbox cuando sea posible
- Logging de acciones del agente
- Rate limiting en APIs
- Verificación de origen de webhooks

---

# 5. Clasificación de acciones

Las acciones del sistema se clasifican en tres niveles:

## Nivel 1 — Seguras
Acciones de lectura o análisis.

Ejemplos:
- analizar texto
- resumir contenido
- consultar documentación

## Nivel 2 — Sensibles
Modifican datos no críticos.

Ejemplos:
- crear lead
- actualizar registros
- guardar información

## Nivel 3 — Críticas
Impactan infraestructura, datos sensibles o dinero.

Ejemplos:
- ejecutar órdenes financieras
- borrar datos
- cambiar permisos
- enviar mensajes reales
- desplegar código

Las acciones críticas requieren **validación adicional o aprobación humana**.

---

# 6. Principio clave

La seguridad debe definirse **antes de implementar funcionalidades**, no después.

El sistema debe asumir que los modelos pueden cometer errores y diseñar límites para minimizar impactos.