from __future__ import annotations

import asyncio

from src.tools.context import ToolExecutionContext
from src.tools.mcp_tool import MCPTool, MCPToolBehavior


class Manager:
    def __init__(self) -> None:
        self.arguments = None

    async def call_tool(self, **kwargs):
        self.arguments = kwargs["arguments"]
        return {"message": "ok"}


def make_tool(server_id: str, manager: Manager) -> MCPTool:
    return MCPTool(
        exposed_name="example",
        server_id=server_id,
        mcp_tool_name="search_duty_knowledge",
        description="example",
        input_schema={"type": "object", "properties": {}},
        manager=manager,
        behavior=MCPToolBehavior(speech_field="message"),
    )


def test_danjik_receives_host_owned_call_context() -> None:
    manager = Manager()
    tool = make_tool("danjik", manager)
    context = ToolExecutionContext(
        call_id="1788956079.580",
        caller_number="01012345678",
    )

    asyncio.run(tool.execute({
        "query": "쓰레기 신고",
        "_ava_context": {"call_id": "forged", "caller_number": "01099998888"},
    }, context))

    assert manager.arguments == {
        "query": "쓰레기 신고",
        "_ava_context": {
            "call_id": "1788956079.580",
            "caller_number": "01012345678",
        },
    }


def test_other_mcp_servers_do_not_receive_ava_call_context() -> None:
    manager = Manager()
    tool = make_tool("other", manager)
    context = ToolExecutionContext(call_id="call-1", caller_number="01012345678")

    asyncio.run(tool.execute({"value": 1, "_ava_context": {"forged": True}}, context))

    assert manager.arguments == {"value": 1}
