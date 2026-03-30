# Femtobot — Demo ligera de arquitectura de agente

[![Docs](https://github.com/rafnixg/femtobot/actions/workflows/build-doc.yml/badge.svg)](https://github.com/rafnixg/femtobot/actions/workflows/build-doc.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Documentación](https://img.shields.io/badge/docs-GitHub%20Pages-blue?logo=github)](https://rafnixg.github.io/femtobot/femtobot.html)
![Licencia](https://img.shields.io/badge/licencia-demo%20educativo-lightgrey)

Femtobot es un ejemplo educativo y minimalista de cómo organizar un agente conversacional en capas. Está inspirado en la arquitectura presentada en el post ["nanobot — arquitectura y funcionamiento"](https://blog.rafnixg.dev/nanobot-arquitectura-y-funcionamiento-del-agente-ia-ultra-ligero) y resume ideas prácticas para construir un agente pequeño, extensible y fácil de entender.

## Resumen rápido

- Flujo asíncrono basado en `asyncio.Queue` para desacoplar productores (canales) y consumidores (el agente).
- Bucle de agente que combina llamadas a un LLM con la ejecución de *tools* (funciones auxiliares) y reinyecta sus resultados al LLM.
- Gestión de sesiones en memoria para conservar historial y construir contexto para el LLM.

## Arquitectura

```mermaid
flowchart LR
    User(["👤 Usuario"])

    subgraph Canal["Canal (Channel)"]
        CLI["CLIChannel"]
    end

    subgraph Bus["MessageBus"]
        IQ[("📥 inbound\nqueue")]
        OQ[("📤 outbound\nqueue")]
    end

    subgraph Agente["AgentLoop"]
        CB["ContextBuilder"]
        AL["🔁 Agent Loop"]
    end

    subgraph Soporte["Soporte"]
        TR["ToolRegistry"]
        SM["SessionManager"]
        LLM["☁️ LLMProvider\n(OpenRouter)"]
    end

    User -->|"mensaje"| CLI
    CLI -->|"publish_inbound"| IQ
    IQ -->|"consume_inbound"| AL
    AL --> CB
    CB --> SM
    AL -->|"chat()"| LLM
    LLM -->|"tool_calls"| TR
    TR -->|"resultados"| AL
    AL -->|"publish_outbound"| OQ
    OQ -->|"consume_outbound"| CLI
    CLI -->|"respuesta"| User
```

## Flujo del agente (secuencia)

```mermaid
sequenceDiagram
    actor Usuario
    participant CLI as CLIChannel
    participant Bus as MessageBus
    participant Loop as AgentLoop
    participant Session as SessionManager
    participant LLM as LLMProvider
    participant Tools as ToolRegistry

    Usuario->>CLI: escribe mensaje
    CLI->>Bus: publish_inbound(InboundMessage)
    Bus->>Loop: consume_inbound()
    Loop->>Session: get_or_create(session_key)
    Session-->>Loop: Session (historial)
    Loop->>LLM: chat(messages, tools, system)

    alt LLM solicita herramienta
        LLM-->>Loop: LLMResponse(tool_calls)
        Loop->>Tools: execute(name, args)
        Tools-->>Loop: resultado (str)
        Loop->>LLM: chat(messages + tool_result)
    end

    LLM-->>Loop: LLMResponse(content)
    Loop->>Session: save(session)
    Loop->>Bus: publish_outbound(OutboundMessage)
    Bus->>CLI: consume_outbound()
    CLI->>Usuario: 🤖 respuesta
```

## Componentes principales

| Componente | Clase(s) | Responsabilidad |
|---|---|---|
| **Canal** | `Channel`, `CLIChannel` | Interfaz de entrada/salida. Publica `InboundMessage` y consume `OutboundMessage`. |
| **Bus de mensajes** | `MessageBus` | Cola central asíncrona que desacopla canales del agente. |
| **Bucle del agente** | `AgentLoop` | Orquesta el flujo: contexto → LLM → tools → respuesta. |
| **Constructor de contexto** | `ContextBuilder` | Ensambla el system prompt y el historial para cada llamada al LLM. |
| **Herramientas** | `Tool`, `ToolRegistry` | Define y registra capacidades invocables por el LLM (ej.: `get_datetime`). |
| **Sesiones** | `Session`, `SessionManager` | Almacena el historial de conversación por sesión en memoria. |
| **Proveedor LLM** | `LLMProvider`, `OpenRouterProvider` | Adaptador para llamar a modelos de lenguaje vía OpenRouter/OpenAI. |

## Por qué esta aproximación

- Desacopla entrada/salida y lógica del agente → mejor testabilidad.
- Permite que el LLM use herramientas de forma controlada y auditable.
- Mantiene el diseño simple y modular, ideal para prototipado rápido.

## Estructura del proyecto

```
femtobot/
├── femtobot.py          # Código principal (todos los componentes)
├── requirements.txt     # Dependencias de runtime
├── tests/
│   └── test_femtobot.py # Tests unitarios (pytest)
└── .github/
    └── workflows/
        └── build-doc.yml  # CI: genera y publica documentación en GitHub Pages
```

## Uso rápido

### Linux / macOS

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Define la clave de API (necesaria para usar OpenRouter):

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

> Obtén una clave gratuita en [openrouter.ai/keys](https://openrouter.ai/keys).

3. Ejecuta el demo:

```bash
python femtobot.py
```

### Windows

<details>
<summary>PowerShell / CMD — haz clic para expandir</summary>

**PowerShell (sesión actual):**

```powershell
$env:OPENROUTER_API_KEY = 'sk-or-v1-...'
python femtobot.py
```

**PowerShell (persistente, requiere reiniciar la sesión):**

```powershell
setx OPENROUTER_API_KEY "sk-or-v1-..."
```

**CMD (sesión actual):**

```cmd
set OPENROUTER_API_KEY=sk-or-v1-...
python femtobot.py
```

</details>

## Ejemplo de sesión

```text
Tú: ¿Qué hora es?

🤖 femtobot: Fecha y hora actual: 2026-03-29 14:23:10
```

El ciclo completo: entrada → `MessageBus` → `AgentLoop` → tool `get_datetime` → resultado → respuesta al usuario.

## Pruebas

```bash
pip install pytest
pytest -q
```

Los tests cubren `DateTimeTool`, `MessageBus`, `ToolRegistry` y `SessionManager` (cobertura parcial; `AgentLoop`, `ContextBuilder` y `Channel` no tienen tests todavía).

## Extender el proyecto

- Añadir persistencia para `SessionManager` (archivo, SQLite, Redis…)
- Implementar nuevos `Channel` (Telegram, Discord, HTTP/webhook)
- Agregar más `Tool` (APIs externas, búsquedas, ejecución de comandos)
- Reemplazar `OpenRouterProvider` por otro proveedor (Anthropic, OpenAI, local)

## Referencias

- Documentación API: [rafnixg.github.io/femtobot/femtobot.html](https://rafnixg.github.io/femtobot/femtobot.html)
- Post conceptual: [nanobot — arquitectura y funcionamiento](https://blog.rafnixg.dev/nanobot-arquitectura-y-funcionamiento-del-agente-ia-ultra-ligero)

## Licencia

Demo educativo — libre para uso y modificación.
