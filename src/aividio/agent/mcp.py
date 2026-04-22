"""MCP Server connector architecture for VIDMATION.

Allows the AI agent to connect to external MCP (Model Context Protocol) servers
for additional capabilities beyond the built-in tool registry.

Future MCP servers could include:
- File system access (read/write project files)
- Web search (research topics, find references)
- Database queries (direct SQL access)
- External APIs (social media, analytics platforms)
- Code execution (Python interpreter for custom processing)

MCP is Anthropic's open protocol for connecting AI models to external tools and
data sources.  This module provides the connector layer that discovers tools from
MCP servers and registers them into the VIDMATION :class:`ToolRegistry` so they
are callable alongside the native tools.

Architecture:
    1. ``MCPConnector`` holds references to registered MCP servers.
    2. When a server is registered, its tools are discovered via the MCP
       ``tools/list`` method and wrapped as :class:`ToolDefinition` entries
       in the ``ToolRegistry``.
    3. When the agent calls an MCP-sourced tool, the connector routes the
       invocation to the appropriate server via ``tools/call``.
    4. Results are returned as strings, consistent with the native tool API.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aividio.agent.registry import ToolRegistry

logger = logging.getLogger("aividio.agent.mcp")


# ---------------------------------------------------------------------------
# MCP Server configuration
# ---------------------------------------------------------------------------


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server connection."""

    name: str
    url: str  # MCP server endpoint (empty string for stdio-based local servers)
    description: str
    capabilities: list[str]
    auth_token: str | None = None
    transport: str = "stdio"  # "stdio" | "http" | "websocket"
    command: str | None = None  # For stdio transport: the command to run
    args: list[str] = field(default_factory=list)  # CLI args for stdio command
    env: dict[str, str] = field(default_factory=dict)  # Extra env vars


@dataclass
class MCPTool:
    """A tool discovered from an MCP server."""

    name: str
    description: str
    input_schema: dict
    server_name: str


# ---------------------------------------------------------------------------
# MCP Connector
# ---------------------------------------------------------------------------


class MCPConnector:
    """Connect to external MCP servers and register their tools.

    The connector manages the lifecycle of MCP server connections:
    registration, tool discovery, tool invocation, and teardown.

    Usage::

        from aividio.agent.mcp import MCPConnector, KNOWN_MCP_SERVERS

        connector = MCPConnector(registry=tool_registry)

        # Register a pre-defined server
        count = connector.register_server(KNOWN_MCP_SERVERS["filesystem"])
        print(f"Imported {count} tools from filesystem MCP server")

        # Call a tool
        result = connector.call_mcp_tool(
            server_name="filesystem",
            tool_name="read_file",
            arguments={"path": "/path/to/file.txt"},
        )

        # List all connected servers
        for server in connector.list_servers():
            print(f"{server.name}: {server.description}")
    """

    def __init__(self, registry: "ToolRegistry") -> None:
        self.registry = registry
        self.servers: dict[str, MCPServerConfig] = {}
        self._server_tools: dict[str, list[MCPTool]] = {}
        self._connections: dict[str, Any] = {}  # Active server connections

    def register_server(self, config: MCPServerConfig) -> int:
        """Register an MCP server and import its tools into the registry.

        Connects to the server, discovers available tools via the MCP
        ``tools/list`` method, and creates corresponding
        :class:`~aividio.agent.registry.ToolDefinition` entries in the
        registry.

        Args:
            config: Server configuration.

        Returns:
            Number of tools imported.

        Raises:
            ConnectionError: If the server cannot be reached.
            ValueError: If a server with the same name is already registered.
        """
        if config.name in self.servers:
            logger.warning(
                "MCP server %r already registered; re-registering", config.name
            )
            self.remove_server(config.name)

        logger.info(
            "Registering MCP server: %s (%s) via %s",
            config.name,
            config.description,
            config.transport,
        )

        self.servers[config.name] = config

        # Discover tools from the server
        try:
            tools = self.discover_tools(config.name)
        except Exception as exc:
            logger.error(
                "Failed to discover tools from MCP server %s: %s",
                config.name,
                exc,
            )
            self.servers.pop(config.name, None)
            raise ConnectionError(
                f"Cannot discover tools from MCP server {config.name!r}: {exc}"
            ) from exc

        self._server_tools[config.name] = tools

        # Register each discovered tool into the VIDMATION tool registry
        imported = 0
        for tool in tools:
            self._register_mcp_tool(tool)
            imported += 1

        logger.info(
            "MCP server %s: %d tools imported", config.name, imported
        )
        return imported

    def discover_tools(self, server_name: str) -> list[MCPTool]:
        """Discover available tools from an MCP server.

        Sends a ``tools/list`` request to the server and parses the response
        into :class:`MCPTool` objects.

        Args:
            server_name: Name of a registered server.

        Returns:
            List of discovered tools.

        Raises:
            KeyError: If *server_name* is not registered.
        """
        if server_name not in self.servers:
            raise KeyError(f"MCP server {server_name!r} is not registered")

        config = self.servers[server_name]

        # Establish connection if needed
        connection = self._get_or_create_connection(config)

        # Send tools/list request
        try:
            response = self._send_request(
                connection, method="tools/list", params={}
            )
        except Exception as exc:
            logger.error(
                "MCP tools/list failed for %s: %s", server_name, exc
            )
            return []

        # Parse response into MCPTool objects
        tools: list[MCPTool] = []
        raw_tools = response.get("tools", [])

        for raw in raw_tools:
            tool = MCPTool(
                name=raw.get("name", ""),
                description=raw.get("description", ""),
                input_schema=raw.get("inputSchema", raw.get("input_schema", {})),
                server_name=server_name,
            )
            if tool.name:
                tools.append(tool)

        logger.info(
            "Discovered %d tools from MCP server %s", len(tools), server_name
        )
        return tools

    def call_mcp_tool(
        self, server_name: str, tool_name: str, arguments: dict
    ) -> str:
        """Call a tool on an MCP server.

        Sends a ``tools/call`` request to the appropriate server and returns
        the result as a JSON string.

        Args:
            server_name: Name of the MCP server hosting the tool.
            tool_name: Name of the tool to invoke.
            arguments: Tool input arguments.

        Returns:
            JSON string containing the tool result.

        Raises:
            KeyError: If the server or tool is not found.
        """
        if server_name not in self.servers:
            return json.dumps(
                {"error": f"MCP server {server_name!r} is not registered"}
            )

        config = self.servers[server_name]
        connection = self._get_or_create_connection(config)

        try:
            response = self._send_request(
                connection,
                method="tools/call",
                params={"name": tool_name, "arguments": arguments},
            )
        except Exception as exc:
            logger.error(
                "MCP tool call %s.%s failed: %s",
                server_name,
                tool_name,
                exc,
            )
            return json.dumps(
                {"error": f"MCP tool call failed: {exc}"}
            )

        # Extract text content from response
        content = response.get("content", [])
        if isinstance(content, list) and content:
            # MCP tools return content as an array of content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            if text_parts:
                combined = "\n".join(text_parts)
                # Try to parse as JSON for structured results
                try:
                    json.loads(combined)
                    return combined
                except (json.JSONDecodeError, ValueError):
                    return json.dumps({"result": combined})

        return json.dumps(response, default=str)

    def list_servers(self) -> list[MCPServerConfig]:
        """List all registered MCP servers."""
        return list(self.servers.values())

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server and its tools from the registry.

        Args:
            name: Server name to remove.

        Returns:
            ``True`` if the server was removed, ``False`` if not found.
        """
        if name not in self.servers:
            logger.warning("Cannot remove unknown MCP server %r", name)
            return False

        # Close the connection if active
        if name in self._connections:
            try:
                self._close_connection(self._connections[name])
            except Exception as exc:
                logger.warning(
                    "Error closing MCP connection for %s: %s", name, exc
                )
            del self._connections[name]

        # Note: tools already registered in the ToolRegistry remain there.
        # The registry doesn't support removal, but the MCP executor will
        # return an error if the server is gone.

        del self.servers[name]
        self._server_tools.pop(name, None)

        logger.info("MCP server %s removed", name)
        return True

    def get_server_tools(self, server_name: str) -> list[MCPTool]:
        """Return the tools discovered from a specific server."""
        return self._server_tools.get(server_name, [])

    # ------------------------------------------------------------------
    # Internal: tool registration bridge
    # ------------------------------------------------------------------

    def _register_mcp_tool(self, mcp_tool: MCPTool) -> None:
        """Wrap an MCP tool as a ToolDefinition and register it."""
        from aividio.agent.registry import ToolDefinition

        # Prefix the tool name with the server name to avoid collisions
        prefixed_name = f"mcp_{mcp_tool.server_name}_{mcp_tool.name}"

        # Create a closure that routes to the MCP server
        server_name = mcp_tool.server_name
        tool_name = mcp_tool.name

        def executor(**kwargs: Any) -> str:
            return self.call_mcp_tool(
                server_name=server_name,
                tool_name=tool_name,
                arguments=kwargs,
            )

        tool_def = ToolDefinition(
            name=prefixed_name,
            description=f"[MCP:{mcp_tool.server_name}] {mcp_tool.description}",
            category=f"mcp_{mcp_tool.server_name}",
            input_schema=mcp_tool.input_schema,
            executor=executor,
            cost_estimate=None,
            requires_api_key=None,
        )

        self.registry._register(tool_def)

    # ------------------------------------------------------------------
    # Internal: connection management
    # ------------------------------------------------------------------

    def _get_or_create_connection(self, config: MCPServerConfig) -> Any:
        """Get an existing connection or create a new one.

        For now, this returns a placeholder. Full MCP protocol implementation
        would use subprocess (stdio) or HTTP client depending on transport.
        """
        if config.name in self._connections:
            return self._connections[config.name]

        # Future: implement actual MCP protocol connection
        # For stdio transport: subprocess.Popen(config.command, config.args)
        # For http transport: httpx.Client(base_url=config.url)
        connection = {
            "config": config,
            "transport": config.transport,
            "active": True,
        }
        self._connections[config.name] = connection

        logger.info(
            "MCP connection established: %s (transport=%s)",
            config.name,
            config.transport,
        )
        return connection

    def _send_request(
        self, connection: Any, method: str, params: dict
    ) -> dict:
        """Send a JSON-RPC request to an MCP server.

        This is a placeholder for the actual MCP protocol implementation.
        Real implementation would:
        - For stdio: write JSON-RPC to stdin, read from stdout
        - For HTTP: POST to the server URL
        - For WebSocket: send over the WS connection

        For now, returns a stub response indicating the server is not
        yet connected.
        """
        config = connection.get("config")
        if config is None:
            return {"error": "Invalid connection"}

        logger.debug(
            "MCP request: server=%s, method=%s, params=%s",
            config.name,
            method,
            json.dumps(params)[:200],
        )

        # Stub response -- in production, this dispatches to the actual server
        if method == "tools/list":
            # Return the declared capabilities as mock tools
            return {
                "tools": [
                    {
                        "name": cap,
                        "description": f"{cap} via {config.name} MCP server",
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                    for cap in config.capabilities
                ]
            }

        if method == "tools/call":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "stub",
                            "message": (
                                f"MCP server {config.name!r} is registered but not "
                                f"connected. Implement the {config.transport} transport "
                                f"to enable real tool calls."
                            ),
                            "tool": params.get("name", ""),
                            "arguments": params.get("arguments", {}),
                        }),
                    }
                ]
            }

        return {"error": f"Unknown MCP method: {method}"}

    def _close_connection(self, connection: Any) -> None:
        """Close an MCP server connection."""
        connection["active"] = False
        logger.info("MCP connection closed")


# ---------------------------------------------------------------------------
# Pre-defined MCP server configs for common integrations
# ---------------------------------------------------------------------------

KNOWN_MCP_SERVERS: dict[str, MCPServerConfig] = {
    "filesystem": MCPServerConfig(
        name="filesystem",
        url="",
        description="Read/write files in the project directory",
        capabilities=["read_file", "write_file", "list_directory", "create_directory"],
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp/aividio"],
    ),
    "web_search": MCPServerConfig(
        name="web_search",
        url="",
        description="Search the web for research and references",
        capabilities=["search", "fetch_url", "extract_content"],
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
    ),
    "code_interpreter": MCPServerConfig(
        name="code_interpreter",
        url="",
        description="Execute Python code for custom processing",
        capabilities=["execute_python", "install_package", "list_packages"],
        transport="stdio",
        command="python",
        args=["-m", "mcp_server_python"],
    ),
    "database": MCPServerConfig(
        name="database",
        url="",
        description="Direct SQL access to the VIDMATION database",
        capabilities=["query", "execute", "list_tables", "describe_table"],
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sqlite", "data/aividio.db"],
    ),
    "youtube_data": MCPServerConfig(
        name="youtube_data",
        url="",
        description="YouTube Data API for channel and video analytics",
        capabilities=[
            "search_videos",
            "get_video_details",
            "get_channel_stats",
            "get_comments",
            "get_trending",
        ],
        transport="http",
    ),
}
