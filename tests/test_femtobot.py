import asyncio
from femtobot import (
    MessageBus,
    InboundMessage,
    OutboundMessage,
    DateTimeTool,
    ToolRegistry,
    SessionManager,
)


def test_datetime_tool_returns_string():
    tool = DateTimeTool()
    result = asyncio.run(tool.execute())
    assert isinstance(result, str)
    assert "Fecha y hora actual" in result


def test_message_bus_roundtrip():
    bus = MessageBus()

    async def _roundtrip():
        msg = InboundMessage(content="hola")
        await bus.publish_inbound(msg)
        received = await bus.consume_inbound()
        return received

    received = asyncio.run(_roundtrip())
    assert isinstance(received, InboundMessage)
    assert received.content == "hola"


def test_tool_registry_register_and_execute():
    registry = ToolRegistry()
    registry.register(DateTimeTool())

    result = asyncio.run(registry.execute("get_datetime", {}))
    assert isinstance(result, str)
    assert "Fecha y hora actual" in result


def test_session_manager_create_and_save():
    sm = SessionManager()
    s = sm.get_or_create("cli:default")
    s.add_user("prueba")
    s.add_assistant("respuesta")
    sm.save(s)

    s2 = sm.get_or_create("cli:default")
    assert len(s2.messages) >= 2
