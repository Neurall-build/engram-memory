# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""ENGRAM MCP Server implementation.

IMPORTANT: This MCP server is designed for TRUSTED-LOCAL use only.
It does NOT implement API key authentication because MCP clients
are assumed to be running locally with the same trust boundary.
Do NOT expose the MCP server over a network without adding
authentication.
"""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from database.schema import init_db
from database.connection import get_connection, reset_connection, execute_write
from layers.working import create as working_create, get as working_get, list_by_user as working_list, delete as working_delete
from layers.episodic import create as episodic_create, get as episodic_get, list_by_user as episodic_list, delete as episodic_delete
from layers.semantic import create as semantic_create, get as semantic_get, list_by_user as semantic_list, delete as semantic_delete, search as semantic_search
from layers.hive import create as hive_create, get as hive_get, list_by_org as hive_list, delete as hive_delete, search as hive_search
from models.memory import MemoryCreateRequest, MemorySearchRequest, MemoryLayer
from config import settings


app = Server("engram")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available ENGRAM tools."""
    return [
        Tool(
            name="engram_create_memory",
            description="Store a memory for later retrieval. Memories persist across sessions and decay over time based on access patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory content to store."
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID to associate with the memory."
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["working", "episodic", "semantic"],
                        "description": "Memory layer: working (temporary), episodic (events), semantic (facts)."
                    },
                    "salience": {
                        "type": "number",
                        "description": "Importance score 0-1. Higher values decay slower. Default 0.5."
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Optional agent ID."
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata about the memory."
                    }
                },
                "required": ["content", "user_id"]
            }
        ),
        Tool(
            name="engram_search_memories",
            description="Search stored memories by semantic similarity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID to filter by."
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["episodic", "semantic"],
                        "description": "Memory layer to search."
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return. Default 10."
                    }
                },
                "required": ["query", "user_id"]
            }
        ),
        Tool(
            name="engram_list_memories",
            description="List recent memories, optionally filtered by layer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to filter by."
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["working", "episodic", "semantic"],
                        "description": "Filter by memory layer."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results. Default 50."
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="engram_get_memory",
            description="Get a specific memory by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The UUID of the memory to retrieve."
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="engram_delete_memory",
            description="Delete a memory by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The UUID of the memory to delete."
                    }
                },
                "required": ["memory_id"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    conn = get_connection()

    try:
        if name == "engram_create_memory":
            req = MemoryCreateRequest(
                content=arguments["content"],
                user_id=arguments["user_id"],
                layer=MemoryLayer(arguments.get("layer", "episodic")),
                salience=arguments.get("salience", 0.5),
                agent_id=arguments.get("agent_id"),
                metadata=arguments.get("metadata", {}),
            )

            if req.layer == MemoryLayer.WORKING:
                result = working_create(conn, req)
            elif req.layer == MemoryLayer.EPISODIC:
                result = episodic_create(conn, req)
            elif req.layer == MemoryLayer.SEMANTIC:
                result = semantic_create(conn, req)
            else:
                return [TextContent(type="text", text=f"Unknown layer: {req.layer}")]

            return [TextContent(type="text", text=json.dumps(result.model_dump(), indent=2))]

        elif name == "engram_search_memories":
            layer = MemoryLayer(arguments.get("layer", "semantic"))
            top_k = arguments.get("top_k", 10)

            if layer == MemoryLayer.SEMANTIC:
                result = semantic_search(conn, arguments["query"], arguments["user_id"], top_k)
            elif layer == MemoryLayer.HIVE:
                result = hive_search(conn, arguments["query"], settings.hive_org_id, top_k)
            else:
                return [TextContent(type="text", text=f"Search not supported for layer: {layer}")]

            return [TextContent(type="text", text=json.dumps(result.model_dump(), indent=2))]

        elif name == "engram_list_memories":
            layer = MemoryLayer(arguments.get("layer", "episodic"))
            user_id = arguments["user_id"]

            if layer == MemoryLayer.WORKING:
                items = working_list(conn, user_id)
            elif layer == MemoryLayer.EPISODIC:
                items = episodic_list(conn, user_id)
            elif layer == MemoryLayer.SEMANTIC:
                items = semantic_list(conn, user_id)
            else:
                return [TextContent(type="text", text=f"Unknown layer: {layer}")]

            limit = arguments.get("limit", 50)
            items = items[:limit]
            return [TextContent(type="text", text=json.dumps([i.model_dump() for i in items], indent=2))]

        elif name == "engram_get_memory":
            mem_id = arguments["memory_id"]
            for getter in [working_get, episodic_get, semantic_get, hive_get]:
                result = getter(conn, mem_id)
                if result is not None:
                    return [TextContent(type="text", text=json.dumps(result.model_dump(), indent=2))]
            return [TextContent(type="text", text=f"Memory {mem_id} not found")]

        elif name == "engram_delete_memory":
            mem_id = arguments["memory_id"]
            for deleter in [working_delete, episodic_delete, semantic_delete, hive_delete]:
                try:
                    if deleter(conn, mem_id):
                        return [TextContent(type="text", text=f"Memory {mem_id} deleted")]
                except Exception:
                    continue
            return [TextContent(type="text", text=f"Memory {mem_id} not found")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    init_db()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
