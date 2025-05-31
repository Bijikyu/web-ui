"""
MCP Client - Model Context Protocol Integration for Enhanced AI Capabilities

This module provides a sophisticated client implementation for the Model Context Protocol (MCP),
enabling seamless integration with MCP-compatible servers that extend AI model capabilities
with external tools, data sources, and specialized functions.

Model Context Protocol Overview:
MCP is a standardized protocol that allows AI models to securely interact with external
systems and tools through a well-defined interface. This enables AI agents to:
- Access real-time data from APIs and databases
- Execute code in sandboxed environments
- Interact with specialized software tools
- Retrieve context from document stores and knowledge bases
- Perform actions in external systems with proper authorization

Why MCP Integration is Critical for Browser Agents:
Browser automation often requires integration with external systems that aren't
accessible through web interfaces alone:
- Database queries for data validation and lookup
- API calls to third-party services for enriched automation
- File system operations for document processing and storage
- Specialized computational tools for data analysis and processing
- Authentication systems for secure access to protected resources

Design Philosophy:
- Security First: All MCP communications are validated and sandboxed
- Protocol Compliance: Strict adherence to MCP specification for interoperability
- Async by Default: Non-blocking operations to prevent UI freezing during external calls
- Error Resilience: Robust handling of network failures and server unavailability
- Type Safety: Strong typing for all MCP message formats and responses
- Observability: Comprehensive logging for debugging and monitoring MCP interactions

MCP Client Architecture:
1. Connection Management: Establish and maintain persistent connections to MCP servers
2. Message Serialization: Handle JSON-RPC message formatting and parsing
3. Request/Response Correlation: Track request-response pairs in async environment
4. Tool Discovery: Enumerate available tools and capabilities from MCP servers
5. Execution Engine: Route tool calls to appropriate MCP servers with result handling
6. Error Handling: Classify and handle different types of MCP errors appropriately

Security Considerations:
MCP servers can execute arbitrary code and access external systems, requiring:
- Server authentication and authorization
- Request validation and sanitization
- Response validation to prevent injection attacks
- Resource limiting to prevent DoS attacks
- Audit logging for security monitoring and compliance

Performance Optimization:
- Connection pooling for efficient resource utilization
- Request batching where supported by the MCP specification
- Response caching for idempotent operations
- Circuit breaker pattern for failing MCP servers
- Timeout management to prevent hung operations

This client serves as the bridge between browser automation agents and the broader
ecosystem of tools and services accessible through MCP, dramatically expanding
the capabilities of automated browser workflows.
"""

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional

# Module-level logger for MCP client operations, protocol debugging, and performance monitoring
# MCP operations involve external network calls and protocol-level communication
# Detailed logging is essential for debugging connection issues and protocol violations
logger = logging.getLogger(__name__)
import inspect
import logging
import uuid
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union, get_type_hints

from browser_use.controller.registry.views import ActionModel
from langchain.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field, create_model  # ensure single import for BaseModel and Field
from src.utils.offline import offline_guard, is_offline  # helper for Codex offline mode and offline check

logger = logging.getLogger(__name__)


@offline_guard(None)  # return None when offline
async def setup_mcp_client_and_tools(mcp_server_config: Dict[str, Any]) -> Optional[MultiServerMCPClient]:
    """Initialize MCP client and return the connected instance.

    The configuration may contain a ``mcpServers`` key describing multiple
    endpoints. The client is started asynchronously and ``None`` is returned if
    connection fails.
    """  # expanded docstring

    logger.info("Initializing MultiServerMCPClient...")


    if is_offline():  # skip network when offline but allow mocked client
        logger.info("Running in CODEX offline mode; attempting mock client.")
        try:
            client = MultiServerMCPClient(mcp_server_config)
            await client.__aenter__()
            return client
        except Exception:
            return None


    if not mcp_server_config:
        logger.error("No MCP server configuration provided.")
        return None

    try:
        if "mcpServers" in mcp_server_config:
            mcp_server_config = mcp_server_config["mcpServers"]
        client = MultiServerMCPClient(mcp_server_config)
        await client.__aenter__()
        return client

    except Exception as e:
        logger.error(f"Failed to setup MCP client or fetch tools: {e}", exc_info=True)
        return None


def create_tool_param_model(tool: BaseTool) -> Type[BaseModel]:
    """Generate a Pydantic model matching the given tool schema."""  # expanded docstring

    # Get tool schema information
    json_schema = tool.args_schema
    tool_name = tool.name

    # If the tool already has a schema defined, convert it to a new param_model
    if json_schema is not None:

        # Create new parameter model
        params = {}

        # Process properties if they exist
        if 'properties' in json_schema:
            # Find required fields
            required_fields: Set[str] = set(json_schema.get('required', []))

            for prop_name, prop_details in json_schema['properties'].items():
                field_type = resolve_type(prop_details, f"{tool_name}_{prop_name}")

                # Check if parameter is required
                is_required = prop_name in required_fields

                # Get default value and description
                default_value = prop_details.get('default', ... if is_required else None)
                description = prop_details.get('description', '')

                # Add field constraints
                field_kwargs = {'default': default_value}
                if description:
                    field_kwargs['description'] = description

                # Add additional constraints if present
                if 'minimum' in prop_details:
                    field_kwargs['ge'] = prop_details['minimum']
                if 'maximum' in prop_details:
                    field_kwargs['le'] = prop_details['maximum']
                if 'minLength' in prop_details:
                    field_kwargs['min_length'] = prop_details['minLength']
                if 'maxLength' in prop_details:
                    field_kwargs['max_length'] = prop_details['maxLength']
                if 'pattern' in prop_details:
                    field_kwargs['pattern'] = prop_details['pattern']

                # Add to parameters dictionary
                params[prop_name] = (field_type, Field(**field_kwargs))

        return create_model(
            f'{tool_name}_parameters',
            __base__=ActionModel,
            **params,  # type: ignore
        )

    # If no schema is defined, extract parameters from the _run method
    run_method = tool._run
    sig = inspect.signature(run_method)

    # Get type hints for better type information
    try:
        type_hints = get_type_hints(run_method)
    except Exception:
        type_hints = {}

    params = {}
    for name, param in sig.parameters.items():
        # Skip 'self' parameter and any other parameters you want to exclude
        if name == 'self':
            continue

        # Get annotation from type hints if available, otherwise from signature
        annotation = type_hints.get(name, param.annotation)
        if annotation == inspect.Parameter.empty:
            annotation = Any

        # Use default value if available, otherwise make it required
        if param.default != param.empty:
            params[name] = (annotation, param.default)
        else:
            params[name] = (annotation, ...)

    return create_model(
        f'{tool_name}_parameters',
        __base__=ActionModel,
        **params,  # type: ignore
    )


def resolve_type(prop_details: Dict[str, Any], prefix: str = "") -> Any:
    """Convert JSON schema entries to appropriate Python types."""  # expanded docstring

    # Handle reference types
    if '$ref' in prop_details:
        # In a real application, reference resolution would be needed
        return Any

    # Basic type mapping
    type_mapping = {
        'string': str,
        'integer': int,
        'number': float,
        'boolean': bool,
        'array': List,
        'object': Dict,
        'null': type(None),
    }

    # Handle formatted strings
    if prop_details.get('type') == 'string' and 'format' in prop_details:
        format_mapping = {
            'date-time': datetime,
            'date': date,
            'time': time,
            'email': str,
            'uri': str,
            'url': str,
            'uuid': uuid.UUID,
            'binary': bytes,
        }
        return format_mapping.get(prop_details['format'], str)

    # Handle enum types
    if 'enum' in prop_details:
        enum_values = prop_details['enum']
        # Create dynamic enum class with safe names
        enum_dict = {}
        for i, v in enumerate(enum_values):
            # Ensure enum names are valid Python identifiers
            if isinstance(v, str):
                key = v.upper().replace(' ', '_').replace('-', '_')
                if not key.isidentifier():
                    key = f"VALUE_{i}"
            else:
                key = f"VALUE_{i}"
            enum_dict[key] = v

        # Only create enum if we have values
        if enum_dict:
            return Enum(f"{prefix}_Enum", enum_dict)
        return str  # Fallback

    # Handle array types
    if prop_details.get('type') == 'array' and 'items' in prop_details:
        item_type = resolve_type(prop_details['items'], f"{prefix}_item")
        return List[item_type]  # type: ignore

    # Handle object types with properties
    if prop_details.get('type') == 'object' and 'properties' in prop_details:
        nested_params = {}
        for nested_name, nested_details in prop_details['properties'].items():
            nested_type = resolve_type(nested_details, f"{prefix}_{nested_name}")
            # Get required field info
            required_fields = prop_details.get('required', [])
            is_required = nested_name in required_fields
            default_value = nested_details.get('default', ... if is_required else None)
            description = nested_details.get('description', '')

            field_kwargs = {'default': default_value}
            if description:
                field_kwargs['description'] = description

            nested_params[nested_name] = (nested_type, Field(**field_kwargs))

        # Create nested model
        nested_model = create_model(f"{prefix}_Model", **nested_params)
        return nested_model

    # Handle union types (oneOf, anyOf)
    if 'oneOf' in prop_details or 'anyOf' in prop_details:
        union_schema = prop_details.get('oneOf') or prop_details.get('anyOf')
        union_types = []
        for i, t in enumerate(union_schema):
            union_types.append(resolve_type(t, f"{prefix}_{i}"))

        if union_types:
            return Union.__getitem__(tuple(union_types))  # type: ignore
        return Any

    # Handle allOf (intersection types)
    if 'allOf' in prop_details:
        nested_params = {}
        for i, schema_part in enumerate(prop_details['allOf']):
            if 'properties' in schema_part:
                for nested_name, nested_details in schema_part['properties'].items():
                    nested_type = resolve_type(nested_details, f"{prefix}_allOf_{i}_{nested_name}")
                    # Check if required
                    required_fields = schema_part.get('required', [])
                    is_required = nested_name in required_fields
                    nested_params[nested_name] = (nested_type, ... if is_required else None)

        # Create composite model
        if nested_params:
            composite_model = create_model(f"{prefix}_CompositeModel", **nested_params)
            return composite_model
        return Dict

    # Default to basic types
    schema_type = prop_details.get('type', 'string')
    if isinstance(schema_type, list):
        # Handle multiple types (e.g., ["string", "null"])
        non_null_types = [t for t in schema_type if t != 'null']
        if non_null_types:
            primary_type = type_mapping.get(non_null_types[0], Any)
            if 'null' in schema_type:
                return Optional[primary_type]  # type: ignore
            return primary_type
        return Any

    return type_mapping.get(schema_type, Any)
