# Femtobot — Demo ligera de arquitectura de agente

Femtobot es un ejemplo educativo y minimalista de cómo organizar un
agente conversacional en capas. Está inspirado en la arquitectura
presentada en el post "nanobot — arquitectura y funcionamiento" y
resume ideas prácticas para construir un agente pequeño, extensible y
fácil de entender.

Resumen rápido
--------------

- Flujo asíncrono basado en `asyncio.Queue` para desacoplar productores
	(canales) y consumidores (el agente).
- Bucle de agente que combina llamadas a un LLM con la ejecución de
	*tools* (funciones auxiliares) y reinyecta sus resultados al LLM.
- Gestión de sesiones en memoria para conservar historial y construir
	contexto para el LLM.

Arquitectura (conceptual)
-------------------------

	[Channel] → publish_inbound → [MessageBus] → consume_inbound → [AgentLoop]
																													 │
															(tool definitions) ← [ToolRegistry]
																													 │
																									[SessionManager]

Componentes principales
------------------------

- `Channel` / `CLIChannel`: interfaz de entrada/salida. Publica
	`InboundMessage` y consume `OutboundMessage`.
- `MessageBus`: cola central con `publish_inbound`, `consume_inbound`,
	`publish_outbound`, `consume_outbound`.
- `AgentLoop`: orquesta el flujo: construye contexto, llama al LLM,
	maneja tool calls, guarda sesión y publica la respuesta final.
- `ToolRegistry` y `Tool`: permite definir capacidades invocables por
	el LLM (ej.: `get_datetime`).
- `SessionManager` / `Session`: almacena historial por sesión en memoria.
- `OpenRouterProvider`: adaptador simple para llamar a modelos via
	OpenRouter/OpenAI (se puede cambiar por otro proveedor).

Flujo de trabajo resumido
-------------------------

1. Un `Channel` (ej. CLI) publica un `InboundMessage` en el `MessageBus`.
2. `AgentLoop` consume el mensaje, recupera la `Session` y construye el
	 contexto para el LLM.
3. Llama al LLM; si el modelo solicita herramientas, el agente las
	 ejecuta y reinyecta los resultados al contexto, repitiendo hasta que
	 el LLM devuelva texto final.
4. La respuesta final se guarda en la sesión y se publica como
	 `OutboundMessage` para que el `Channel` la muestre al usuario.

Por qué esta aproximación
-------------------------

- Desacopla entrada/salida y lógica del agente (mejor testabilidad).
- Permite que el LLM use herramientas de forma controlada y auditable.
- Mantiene el diseño simple y modular, ideal para prototipado rápido.

Uso rápido
---------

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Define la clave (opcional, para usar OpenRouter/OpenAI):

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

3. Ejecuta el demo (CLI):

```bash
python femtobot.py
```

Extender el proyecto
---------------------

- Añadir persistencia para `SessionManager` (archivo o base de datos)
- Implementar más `Channel` (Telegram, Discord, HTTP)
- Añadir herramientas (APIs externas, búsquedas, ejecución de comandos)
- Reemplazar o configurar `LLMProvider` para usar otros modelos

Pruebas
-------

Se incluye un archivo de pruebas mínimo en `tests/test_femtobot.py`.
Ejecuta con `pytest`:

```bash
pip install pytest
pytest -q
```

Notas y referencias
-------------------

- Este README es un resumen conciso; para una explicación más amplia y
	la motivación conceptual, consulta el post original:
	https://blog.rafnixg.dev/nanobot-arquitectura-y-funcionamiento-del-agente-ia-ultra-ligero

Licencia
--------

Demo educativo — libre para uso y modificación.
