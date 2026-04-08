import json
from typing import Optional, Literal, List
from mcp.types import CallToolResult, Tool, TextContent
from mcp_client import MCPClient
from anthropic.types import Message, ToolResultBlockParam


class ToolManager:
    @classmethod
    async def get_all_tools(cls, clients: dict[str, MCPClient]) -> list[Tool]:
        """Gets all tools from all provided clients."""
        tools = []
        for client in clients.values():
            tool_models = await client.list_tools()
            tools += [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in tool_models
            ]
        return tools

    @classmethod
    async def _find_client_with_tool(
        cls, clients: list[MCPClient], tool_name: str
    ) -> Optional[MCPClient]:
        """Finds the first client that has the specified tool."""
        for client in clients:
            tools = await client.list_tools()
            if any(t.name == tool_name for t in tools):
                return client
        return None

    @classmethod
    def _build_tool_result_part(
        cls,
        tool_use_id: str,
        text: str,
        status: Literal["success", "error"],
    ) -> ToolResultBlockParam:
        """Builds a tool result block."""
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": text,
            "is_error": status == "error",
        }

    @classmethod
    async def execute_tool_requests(
        cls, clients: dict[str, MCPClient], message: Message
    ) -> List[ToolResultBlockParam]:
        """Executes all tool_use blocks in a message and returns results."""
        tool_requests = [b for b in message.content if b.type == "tool_use"]
        tool_result_blocks: list[ToolResultBlockParam] = []

        for tool_request in tool_requests:
            tool_use_id = tool_request.id
            tool_name = tool_request.name
            tool_input = tool_request.input

            client = await cls._find_client_with_tool(
                list(clients.values()), tool_name
            )

            if not client:
                tool_result_blocks.append(
                    cls._build_tool_result_part(
                        tool_use_id, "Could not find that tool.", "error"
                    )
                )
                continue

            tool_output: CallToolResult | None = None
            try:
                tool_output = await client.call_tool(tool_name, tool_input)
                items = tool_output.content if tool_output else []
                content_json = json.dumps(
                    [item.text for item in items if isinstance(item, TextContent)]
                )
                status = "error" if tool_output and tool_output.isError else "success"
                tool_result_blocks.append(
                    cls._build_tool_result_part(tool_use_id, content_json, status)
                )
            except Exception as e:
                error_message = f"Error executing tool '{tool_name}': {e}"
                print(error_message)
                tool_result_blocks.append(
                    cls._build_tool_result_part(
                        tool_use_id,
                        json.dumps({"error": error_message}),
                        "error",
                    )
                )

        return tool_result_blocks
