# Femtobot — Demo de arquitectura de agente

Femtobot es una demostración educativa de una arquitectura de agente
conversacional inspirada en el proyecto "nanobot". Está organizada en
capas: canales (Channel), un bus de mensajes (MessageBus), el bucle del
agente (AgentLoop), un registro de herramientas (ToolRegistry) y la
gestión de sesiones (SessionManager).

Características:
- Flujo asíncrono productor/consumidor mediante `asyncio.Queue`.
- Soporta definición y ejecución de "tools" que el LLM puede invocar.
- Gestión simple de historial por sesión en memoria.

Requisitos
---------

Instala la dependencia listada en `requirements.txt`:

```bash
pip install -r requirements.txt
```

Uso
---

Define la variable de entorno `OPENROUTER_API_KEY` si quieres probar
integración con OpenRouter/OpenAI:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
python femtobot.py
```

Pruebas
------

Se incluye un archivo mínimo de pruebas en `tests/test_femtobot.py`.
Usa `pytest` para ejecutarlas si lo deseas:

```bash
pip install pytest
pytest -q
```

Notas
-----

No modifiques la lógica si solo quieres mejorar la documentación. Si
detectas posibles mejoras en la arquitectura (persistencia de sesiones,
soporte de más canales, manejo más robusto de herramientas), puedo
proponer cambios en otro PR o patch.

Licencia
--------

Demo educativo — libre para uso y modificación.
