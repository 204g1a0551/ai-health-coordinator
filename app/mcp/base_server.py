"""
Base MCP Server Definition
Abstract server providing tool registration, schema validation, and execution.
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional
from app.mcp.models import MCPTool

logger = logging.getLogger(__name__)


class MCPValidationError(Exception):
    """Raised when input parameters fail schema validation."""
    pass


class BaseMCPServer:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._tools: Dict[str, MCPTool] = {}
        self._handlers: Dict[str, Callable] = {}

    def register_tool(self, tool: MCPTool, handler: Callable) -> None:
        """Register a controlled tool and its execution handler."""
        self._tools[tool.name] = tool
        self._handlers[tool.name] = handler
        logger.info(f"Registered MCP tool: [{self.name}] {tool.name}")

    def list_tools(self) -> List[MCPTool]:
        """Return all registered tools with their schemas."""
        return list(self._tools.values())

    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Lookup tool definition by name."""
        return self._tools.get(tool_name)

    def validate_inputs(self, tool: MCPTool, arguments: Dict[str, Any]) -> None:
        """
        Validates arguments against the tool's input_schema.
        Verifies required fields and non-empty string checks.
        """
        schema = tool.input_schema
        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required_fields:
            if field not in arguments:
                raise MCPValidationError(f"Missing required parameter: '{field}'")
            val = arguments[field]
            if val is None or (isinstance(val, str) and not val.strip()):
                raise MCPValidationError(f"Required parameter '{field}' cannot be empty")

        # Type checks for basic expected types
        for k, v in arguments.items():
            if k in properties and v is not None:
                prop = properties[k]
                expected_type = prop.get("type")
                if expected_type == "string" and not isinstance(v, str):
                    raise MCPValidationError(f"Parameter '{k}' must be a string")
                elif expected_type == "integer" and not isinstance(v, int):
                    raise MCPValidationError(f"Parameter '{k}' must be an integer")
                elif expected_type == "number" and not isinstance(v, (int, float)):
                    raise MCPValidationError(f"Parameter '{k}' must be a number")
                elif expected_type == "boolean" and not isinstance(v, bool):
                    raise MCPValidationError(f"Parameter '{k}' must be a boolean")
                elif expected_type == "array" and not isinstance(v, list):
                    raise MCPValidationError(f"Parameter '{k}' must be an array")
                elif expected_type == "object" and not isinstance(v, dict):
                    raise MCPValidationError(f"Parameter '{k}' must be an object")

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """
        Executes a registered tool handler with validated arguments and context.
        """
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found on server '{self.name}'")

        tool = self._tools[tool_name]
        self.validate_inputs(tool, arguments)

        handler = self._handlers[tool_name]
        sig = inspect.signature(handler)

        # Inspect handler signature to see if it accepts context (user_id, session_id, etc.)
        kwargs = dict(arguments)
        if "context" in sig.parameters:
            kwargs["context"] = context
        elif "user_id" in sig.parameters:
            if "user_id" not in kwargs or kwargs["user_id"] is None:
                kwargs["user_id"] = context.get("user_id")

        return handler(**kwargs)
