"""
Femtobot — Demo de arquitectura tipo "nanobot" (simplificada)

Este módulo implementa una versión educativa (≈300 líneas) de la
arquitectura en capas usada en proyectos de agentes conversacionales:

    Channel  →  MessageBus  →  AgentLoop  →  Tools / Memory

Objetivo:
    Servir como ejemplo didáctico y punto de partida para experimentar
    con un bucle de agente que soporta invocación de "tools" y manejo de
    sesiones.

Requisitos:
    - Python 3.8+
    - Dependencia de runtime: `openai` (se especifica en `requirements.txt`)

Configuración:
    Define la variable de entorno `OPENROUTER_API_KEY` con tu clave de
    OpenRouter/OpenAI si deseas usar el proveedor `OpenRouterProvider`:

        export OPENROUTER_API_KEY="sk-or-v1-..."

    Obtén una key en: https://openrouter.ai/keys

Nota:
    Este archivo está pensado para modificar solo la documentación y
    experimentar; no cambia la lógica básica del agente en esta versión.
"""

import asyncio
import os
import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI


# ══════════════════════════════════════════════════════════════════
# 1. CAPA DE MENSAJES (bus/events.py en nanobot)
#    Define los tipos de mensajes que fluyen por el sistema.
# ══════════════════════════════════════════════════════════════════


@dataclass
class InboundMessage:
    """Mensaje que llega desde un canal (usuario → agente)."""

    content: str
    channel: str = "cli"
    chat_id: str = "default"
    session_key: str = "cli:default"


@dataclass
class OutboundMessage:
    """Mensaje que sale hacia un canal (agente → usuario)."""

    content: str
    channel: str = "cli"
    chat_id: str = "default"


# ══════════════════════════════════════════════════════════════════
# 2. MESSAGE BUS (bus/queue.py en nanobot)
#    Cola asíncrona que desacopla canales del agente.
#    Los canales publican mensajes; el agente los consume.
# ══════════════════════════════════════════════════════════════════


class MessageBus:
    """
    Bus de mensajes central.

    Patrón: productor/consumidor asíncrono.
    - Los canales publican InboundMessages.
    - El AgentLoop consume InboundMessages y publica OutboundMessages.
    - Los canales consumen OutboundMessages para enviar al usuario.
    """

    def __init__(self):
        self._inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """Canal → Bus: encola mensaje del usuario.

        Args:
            msg: InboundMessage con el contenido y metadatos del mensaje.
        """
        await self._inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """Bus → AgentLoop: saca el próximo mensaje a procesar.

        Returns:
            InboundMessage con el contenido y metadatos del mensaje.
        """
        return await self._inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """AgentLoop → Bus: encola respuesta del agente.

        Args:
            msg: OutboundMessage con el contenido y metadatos de la respuesta.
        """
        await self._outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """Bus → Canal: saca la respuesta para enviar al usuario.

        Returns:
            OutboundMessage con el contenido y metadatos de la respuesta.
        """
        return await self._outbound.get()


# ══════════════════════════════════════════════════════════════════
# 3. SISTEMA DE TOOLS (agent/tools/ en nanobot)
#    Las tools son capacidades que el LLM puede invocar.
#    Cada tool tiene: nombre, descripción, parámetros, ejecución.
# ══════════════════════════════════════════════════════════════════


class Tool(ABC):
    """Clase base para todas las tools (agent/tools/base.py)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único de la tool."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción que el LLM usará para decidir cuándo llamarla."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """Esquema JSON de los parámetros."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Lógica de ejecución de la tool."""
        ...

    def to_anthropic_format(self) -> dict:
        """Convierte la tool al formato que espera la API de Anthropic."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


class DateTimeTool(Tool):
    """Tool de ejemplo: fecha y hora actual.

    El LLM puede llamarla para obtener la fecha y hora del sistema.
    Ejemplo de definición de tool simple, sin parámetros.
    Como usarla tool:
    "¿Qué hora es?" → LLM llama a "get_datetime" → ejecuta tool
    → devuelve resultado al LLM → LLM responde al usuario con la hora actual.
    """

    @property
    def name(self) -> str:
        return "get_datetime"

    @property
    def description(self) -> str:
        return "Obtiene la fecha y hora actual del sistema."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self) -> str:
        """Implementación de la tool: retorna la fecha y hora actual.

        Returns:
            str: Cadena con la fecha y hora actual formateada en
            "YYYY-MM-DD HH:MM:SS". Diseñado para ser invocado por el
            LLM cuando se requiere información temporal precisa.
        """
        now = datetime.datetime.now()
        return f"Fecha y hora actual: {now.strftime('%Y-%m-%d %H:%M:%S')}"


class ToolRegistry:
    """
    Registro de tools disponibles (agent/tools/registry.py).
    El AgentLoop pide las definiciones al LLM y ejecuta las calls.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Registra una tool en el sistema."""
        self._tools[tool.name] = tool
        print(f"  [Registry] Tool registrada: '{tool.name}'")

    def get_definitions(self) -> list[dict]:
        """Retorna las definiciones en formato Anthropic para el LLM."""
        return [t.to_anthropic_format() for t in self._tools.values()]

    async def execute(self, name: str, arguments: dict) -> str:
        """Ejecuta una tool por nombre con los argumentos dados."""
        if name not in self._tools:
            return f"Error: tool '{name}' no encontrada."
        tool = self._tools[name]
        print(f"  [Tool] Ejecutando '{name}' con args: {arguments}")
        return await tool.execute(**arguments)


# ══════════════════════════════════════════════════════════════════
# 4. MEMORIA / SESIÓN (session/manager.py + agent/memory.py)
#    Persiste el historial de conversación por sesión.
# ══════════════════════════════════════════════════════════════════


class Session:
    """
    Sesión de conversación.
    Guarda el historial de mensajes en el formato que espera el LLM.
    """

    def __init__(self, key: str):
        self.key = key
        self.messages: list[dict] = []  # Historial en formato Anthropic

    def add_user(self, content: str) -> None:
        """Agrega un mensaje del usuario al historial.

        Args:
            content: Texto del mensaje del usuario.
        """
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        """Agrega un mensaje del asistente al historial.

        Args:
            content: Texto del mensaje del asistente.
        """
        self.messages.append({"role": "assistant", "content": content})

    def get_history(self, max_messages: int = 20) -> list[dict]:
        """Retorna el historial de mensajes para el LLM, limitado a los últimos N mensajes.

        Args:
            max_messages: Número máximo de mensajes a retornar.

        Returns:
            Lista de mensajes en formato Anthropic (role/content).
        """
        return self.messages[-max_messages:]


class SessionManager:
    """
    Administra sesiones por clave (channel:chat_id).
    En nanobot real esto persiste en disco.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, key: str) -> Session:
        """Obtiene la sesión por clave o crea una nueva si no existe.
        Args:
            key: Clave de la sesión (ej: "cli:default").
        Returns:
            Session asociada a la clave.
        """
        if key not in self._sessions:
            self._sessions[key] = Session(key)
        return self._sessions[key]

    def save(self, session: Session) -> None:
        """Guarda la sesión en el registro (en memoria en este demo).
        En nanobot real esto escribiría a disco para persistencia.
        Args:
            session: Session a guardar.
        """
        self._sessions[session.key] = session


# ══════════════════════════════════════════════════════════════════
# 5. PROVEEDOR LLM (providers/ en nanobot)
#    Abstracción sobre la API del modelo de lenguaje.
# ══════════════════════════════════════════════════════════════════


@dataclass
class LLMResponse:
    """Respuesta normalizada del LLM."""

    content: str | None  # Texto final (si no hay tool calls)
    tool_calls: list[dict]  # Lista de tool calls [{name, input}]

    @property
    def has_tool_calls(self) -> bool:
        """Indica si la respuesta incluye llamadas a tools."""
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """Interfaz base para proveedores de LLM (providers/base.py).

    Define el método chat() que el AgentLoop usará para interactuar con el modelo.
    Cada implementación concreta (OpenRouter, OpenAI, Anthropic) adaptará esta interfaz
    a su API específica, pero el AgentLoop solo conoce esta abstracción.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Llama al LLM con el contexto dado y retorna una respuesta normalizada.

        Args:
            messages: Lista de mensajes en formato Anthropic (role/content).
            tools: Lista de definiciones de tools en formato Anthropic.
            system: Prompt de sistema para definir identidad/reglas.
            max_tokens: Límite de tokens para la respuesta.

        Returns:
            LLMResponse con el texto final y las tool calls (si las hay).
        """
        ...


class OpenRouterProvider(LLMProvider):
    """Proveedor de LLM usando OpenRouter.
    OpenRouter expone una API compatible con OpenAI, lo que permite
    acceder a cientos de modelos (Claude, GPT, Gemini, Llama, etc.)
    con una sola integración.

    En este demo usamos el modelo gratuito "stepfun/step-3.5-flash:free",
    pero puedes cambiarlo por cualquier otro modelo disponible en OpenRouter.

    En nanobot real usamos "anthropic/claude-sonnet-4-5"
    para aprovechar sus capacidades de tool use, pero
    "stepfun/step-3.5-flash:free" también soporta herramientas
    y es una buena opción para demos sin costo.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "stepfun/step-3.5-flash:free",
    ):
        """Inicializa el cliente de OpenRouter con la API key y modelo especificados.
        Args:
            api_key: Clave de API de OpenRouter.
            model: Nombre del modelo a usar (ej: "anthropic/claude-sonnet-4-5").
        """

        # La clase AsyncOpenAI es compatible con la API de OpenRouter.
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = model

    def _tools_to_openai_format(self, tools: list[dict]) -> list[dict]:
        """
        Convierte tools del formato Anthropic al formato OpenAI/OpenRouter.
        Anthropic usa 'input_schema'; OpenAI usa 'parameters'.

        Args:
            tools: Lista de definiciones de tools en formato Anthropic.
        Returns:
            Lista de definiciones de tools en formato OpenAI/OpenRouter.
        """
        converted = []
        for t in tools:
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
            )
        return converted

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Implementación del método chat() usando la API de OpenRouter.
        Args:
            messages: Lista de mensajes en formato Anthropic (role/content).
            tools: Lista de definiciones de tools en formato Anthropic.
            system: Prompt de sistema para definir identidad/reglas.
            max_tokens: Límite de tokens para la respuesta.
        Returns:
            LLMResponse con el texto final y las tool calls (si las hay).
        """
        import json

        # OpenAI pone el system prompt como primer mensaje con role "system"
        all_messages = [{"role": "system", "content": system}] + messages

        openai_tools = self._tools_to_openai_format(tools) if tools else []

        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            messages=all_messages,
        )
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        # Extrae tool calls y texto de la respuesta
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments),
                    }
                )

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
        )


# ══════════════════════════════════════════════════════════════════
# 6. CONTEXT BUILDER (agent/context.py en nanobot)
#    Ensambla el prompt de sistema y los mensajes para el LLM.
# ══════════════════════════════════════════════════════════════════


class ContextBuilder:
    """
    Construye el contexto completo para cada llamada al LLM.
    En nanobot real incluye: identidad, memoria, skills, metadatos.
    En este demo simplificamos a un prompt de sistema fijo + historial de mensajes.
    El método build_messages() combina el historial de la sesión con el mensaje actual.

    """

    def build_system_prompt(self) -> str:
        """Construye el prompt de sistema que define la identidad y reglas del agente.
        Se podría implementar la lectura de un archivo o plantilla, pero para este
        demo lo dejamos hardcodeado para enfocarnos en la arquitectura.
        """

        AGENT_IDENTITY = (
            "Agents Instructions:\n"
            "Eres femtobot🐈✨, un asistente de IA personal."
        )

        AGENT_SOUL = (
            "Soul:\n"
            "Personalidad: amigable, ingenioso, directo.\n"
            "Habilidades: usar herramientas, responder preguntas, mantener conversaciones.\n"
            "Objetivo: ayudar al usuario de la mejor manera posible.\n"
            "Valores: Exactitud sobre velocidad, transparencia con el usuario, seguridad y ética.\n"
            "Estilo de comunicación: claro, conciso, sin rodeos, siempre en español."
        )

        AGENT_TOOLS = (
            "Tools Instructions:\n"
            "Puedes usar las siguientes herramientas cuando lo consideres necesario para responder al usuario:\n"
            "- get_datetime: Obtiene la fecha y hora actual del sistema."
        )

        AGENT_DATE = f"Fecha actual: {datetime.date.today()}"

        # Concatenar los bloques separados por doble salto de línea
        prompt = f"{AGENT_IDENTITY}\n\n{AGENT_SOUL}\n\n{AGENT_TOOLS}\n\n{AGENT_DATE}"
        return prompt

    def build_messages(self, history: list[dict], current_message: str) -> list[dict]:
        """
        Construye la lista de mensajes para el LLM:
        [historial previo] + [mensaje actual del usuario]
        El historial ya está en formato Anthropic (role/content).

        Args:
            history: Lista de mensajes previos en formato Anthropic.
            current_message: Texto del mensaje actual del usuario.
        Returns:
            Lista de mensajes combinada para enviar al LLM.
        """
        messages = list(history)  # Copia del historial
        messages.append({"role": "user", "content": current_message})
        return messages

    def add_assistant_with_tool_calls(
        self, messages: list[dict], content: str | None, tool_calls: list[dict]
    ) -> list[dict]:
        """Agrega la respuesta del asistente (con tool calls) al hilo.
        En formato OpenAI/OpenRouter los tool_calls van en el mismo mensaje.

        Args:
            messages: Lista de mensajes actual.
            content: Texto de la respuesta del asistente (puede ser None si solo hay tool calls).
            tool_calls: Lista de tool calls que el LLM quiere ejecutar.
        Returns:
            Lista de mensajes actualizada con la respuesta del asistente y las tool calls.
        """
        openai_tool_calls = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": __import__("json").dumps(tc["input"]),
                },
            }
            for tc in tool_calls
        ]
        messages.append(
            {
                "role": "assistant",
                "content": content or "",
                "tool_calls": openai_tool_calls,
            }
        )
        return messages

    def add_tool_results(
        self, messages: list[dict], tool_calls: list[dict], results: list[str]
    ) -> list[dict]:
        """Agrega los resultados de las tools al hilo.
        En OpenAI cada resultado va como un mensaje separado con role 'tool'.

        Args:
            messages: Lista de mensajes actual.
            tool_calls: Lista de tool calls que se ejecutaron.
            results: Lista de resultados correspondientes a cada tool call.
        Returns:
            Lista de mensajes actualizada con los resultados de las tools.
        """
        for tc, result in zip(tool_calls, results):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                }
            )
        return messages


# ══════════════════════════════════════════════════════════════════
# 7. AGENT LOOP (agent/loop.py en nanobot) ← NÚCLEO DEL SISTEMA
#    Orquesta todo: recibe mensajes, llama al LLM, ejecuta tools,
#    guarda sesión y devuelve respuesta.
# ══════════════════════════════════════════════════════════════════


class AgentLoop:
    """
    Bucle principal del agente.

    Flujo por cada mensaje:
    1. Recibe InboundMessage del bus
    2. Carga historial de la sesión
    3. Construye contexto (system prompt + historial + mensaje)
    4. Llama al LLM → si hay tool calls, las ejecuta y repite
    5. Cuando el LLM responde con texto, guarda y publica respuesta
    6. Maneja comandos especiales (ej: /stop para detener el agente)
    7. Maneja errores internos y los reporta al usuario
    8. Limita el número de iteraciones para evitar loops infinitos
    9. Imprime logs detallados para seguimiento del proceso
    10. Es concurrente: puede procesar múltiples mensajes a la vez sin bloquearse
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        tools: ToolRegistry,
        sessions: SessionManager,
        context: ContextBuilder,
        max_iterations: int = 10,  # Nanobot real usa 40
    ):
        """Inicializa el AgentLoop con sus dependencias.

        Args:
            bus: MessageBus para recibir mensajes y publicar respuestas.
            provider: LLMProvider para interactuar con el modelo de lenguaje.
            tools: ToolRegistry con las tools disponibles para el agente.
            sessions: SessionManager para manejar el historial de conversaciones.
            context: ContextBuilder para construir el contexto de cada llamada al LLM.
            max_iterations: Límite de iteraciones del bucle agente (LLM ↔ Tools) para evitar loops infinitos.
        """
        self.bus = bus
        self.provider = provider
        self.tools = tools
        self.sessions = sessions
        self.context = context
        self.max_iterations = max_iterations
        self._running = False

    async def run(self) -> None:
        """Bucle principal que consume mensajes del bus y los procesa.
        Maneja comandos especiales y errores internos.
        """
        self._running = True
        print("\n[AgentLoop] Iniciado. Esperando mensajes...\n")

        while self._running:
            try:
                # Espera el próximo mensaje (timeout para poder salir)
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            # Manejo de comandos especiales
            if msg.content.strip().lower() == "/stop":
                self._running = False
                await self.bus.publish_outbound(
                    OutboundMessage("Deteniendo femtobot...", msg.channel, msg.chat_id)
                )
                break

            # Procesa el mensaje como tarea asíncrona
            asyncio.create_task(self._dispatch(msg))

    async def _dispatch(self, msg: InboundMessage) -> None:
        """Procesa un mensaje individual: llama al método principal de
        procesamiento y maneja errores.
        Args:
            msg: InboundMessage a procesar.
        """
        try:
            response = await self._process_message(msg)
            await self.bus.publish_outbound(response)
        except Exception as e:
            error_msg = f"Error interno: {e}"
            print(f"  [AgentLoop] {error_msg}")
            await self.bus.publish_outbound(
                OutboundMessage(error_msg, msg.channel, msg.chat_id)
            )

    async def _process_message(self, msg: InboundMessage) -> OutboundMessage:
        """Procesa el mensaje: carga sesión, construye contexto, ejecuta bucle agente,
        guarda sesión y devuelve respuesta:
            sesión → contexto → loop LLM+tools → respuesta

        Args:
            msg: InboundMessage con el contenido y metadatos del mensaje a procesar.
        Returns:
            OutboundMessage con la respuesta final para el usuario.
        """
        print(f"\n[AgentLoop] Procesando: '{msg.content}'")

        # Carga o crea la sesión para este chat
        session = self.sessions.get_or_create(msg.session_key)

        # Construye los mensajes para el LLM
        messages = self.context.build_messages(
            history=session.get_history(),
            current_message=msg.content,
        )

        # Ejecuta el bucle agente (LLM ↔ Tools)
        final_content = await self._run_agent_loop(messages)

        # Guarda la conversación en la sesión
        session.add_user(msg.content)
        session.add_assistant(final_content)
        self.sessions.save(session)

        return OutboundMessage(final_content, msg.channel, msg.chat_id)

    async def _run_agent_loop(self, messages: list[dict]) -> str:
        """
        Bucle interno: LLM → tool calls → resultados → LLM → ...
        Termina cuando el LLM da una respuesta de texto sin tool calls.

        Args:
            messages: Lista de mensajes para enviar al LLM (incluye historial + mensaje actual).
        Returns:
            str: Respuesta final del LLM para el usuario.
        """
        system_prompt = self.context.build_system_prompt()
        tool_definitions = self.tools.get_definitions()

        for iteration in range(1, self.max_iterations + 1):
            print(f"  [Loop] Iteración {iteration}/{self.max_iterations}")

            # Llama al LLM
            response = await self.provider.chat(
                messages=messages,
                tools=tool_definitions,
                system=system_prompt,
            )

            if response.has_tool_calls:
                # El LLM quiere usar tools → ejecutarlas y continuar
                print(f"  [Loop] LLM solicita {len(response.tool_calls)} tool(s)")

                # Agrega la respuesta del asistente al hilo
                messages = self.context.add_assistant_with_tool_calls(
                    messages, response.content, response.tool_calls
                )

                # Ejecuta cada tool call
                results = []
                for tc in response.tool_calls:
                    result = await self.tools.execute(tc["name"], tc["input"])
                    results.append(result)
                    print(f"  [Loop] Resultado de '{tc['name']}': {result}")

                # Agrega resultados al hilo de mensajes
                messages = self.context.add_tool_results(
                    messages, response.tool_calls, results
                )
                # Continúa el loop → el LLM verá los resultados

            else:
                # El LLM respondió con texto → fin del loop
                print(f"  [Loop] LLM responde con texto. Fin del loop.")
                return response.content or "(sin respuesta)"

        return "Alcancé el límite de iteraciones sin respuesta final."


# ══════════════════════════════════════════════════════════════════
# 8. CANAL CLI (channels/base.py en nanobot)
#    El canal más simple: lee de stdin, escribe en stdout.
#    En nanobot real existen canales Telegram, WhatsApp, Discord...
# ══════════════════════════════════════════════════════════════════


class Channel(ABC):
    """Interfaz base para canales de comunicación (channels/base.py).
    Define el método run() que cada canal implementará para manejar la entrada/salida.
    El AgentLoop es agnóstico al canal: solo interactúa con el MessageBus.
    """

    @abstractmethod
    async def run(self) -> None:
        """Bucle principal del canal para manejar entrada/salida."""
        ...


class CLIChannel(Channel):
    """Canal de línea de comandos (CLI).
    Lee input del usuario desde stdin y publica mensajes en el bus.
    Escucha respuestas del bus y las imprime en stdout.
    Es un canal síncrono adaptado a asyncio usando run_in_executor para no bloquear el bucle del agente.

    """

    def __init__(self, bus: MessageBus):
        self.bus = bus

    async def run(self) -> None:
        """Bucle de entrada/salida del canal CLI."""
        print("╔══════════════════════════════════════╗")
        print("║  🐈 femtobot — Demo Arquitectura    ║")
        print("║  Escribe /stop para salir            ║")
        print("╚══════════════════════════════════════╝\n")

        while True:
            # Lee input del usuario (asyncio-friendly)
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(None, input, "Tú: ")

            if not user_input.strip():
                continue

            # Publica el mensaje en el bus
            await self.bus.publish_inbound(
                InboundMessage(
                    content=user_input,
                    channel="cli",
                    chat_id="default",
                    session_key="cli:default",
                )
            )

            # Espera y muestra la respuesta
            response = await self.bus.consume_outbound()
            print(f"\n🤖 femtobot: {response.content}\n")

            if user_input.strip().lower() == "/stop":
                break


# ══════════════════════════════════════════════════════════════════
# 9. BOOTSTRAP (cli/ en nanobot)
#    Ensambla todos los componentes y arranca el sistema.
# ══════════════════════════════════════════════════════════════════


async def main():
    """
    Punto de entrada: ensambla y arranca femtobot.

    Diagrama de componentes:

    [CLIChannel] ──publish──► [MessageBus] ──consume──► [AgentLoop]
                                                              │
                                              ┌───────────────┤
                                              ▼               ▼
                                         [ToolRegistry]  [SessionManager]
                                             │
                                         [DateTime]
    El CLIChannel lee input del usuario y lo publica en el MessageBus.
    El AgentLoop consume mensajes del MessageBus, construye el contexto,
    llama al LLM y ejecuta tools según sea necesario.
    Luego publica la respuesta de vuelta en el MessageBus para que el CLIChannel
    la muestre al usuario.    
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: define la variable OPENROUTER_API_KEY")
        print("   export OPENROUTER_API_KEY='sk-or-v1-...'")
        print("   Obtén tu key en: https://openrouter.ai/keys")
        return

    print("\n[Bootstrap] Iniciando femtobot...\n")

    # 1. Crea el bus central
    bus = MessageBus()
    print("[Bootstrap] ✓ MessageBus creado")

    # 2. Registra las tools
    tools = ToolRegistry()
    tools.register(DateTimeTool())
    print("[Bootstrap] ✓ Tools registradas")

    # 3. Crea los demás componentes
    # Puedes cambiar el modelo a cualquiera disponible en OpenRouter:
    #   "anthropic/claude-sonnet-4-5"
    #   "openai/gpt-4o"
    #   "google/gemini-2.0-flash-001"
    #   "meta-llama/llama-3.3-70b-instruct"
    provider = OpenRouterProvider(
        api_key=api_key,
        model="stepfun/step-3.5-flash:free",
    )
    sessions = SessionManager()
    context = ContextBuilder()
    print(f"[Bootstrap] ✓ Provider OpenRouter listo (modelo: {provider.model})")

    # 4. Crea el agente
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        tools=tools,
        sessions=sessions,
        context=context,
    )
    print("[Bootstrap] ✓ AgentLoop listo")

    # 5. Crea el canal CLI
    channel = CLIChannel(bus=bus)
    print("[Bootstrap] ✓ CLIChannel listo")

    # 6. Arranca ambos concurrentemente
    print("[Bootstrap] Arrancando sistema...\n")
    await asyncio.gather(
        agent.run(),
        channel.run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
