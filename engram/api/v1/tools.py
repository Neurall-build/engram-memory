# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""OpenAI-compatible tool definitions for ENGRAM.

Agents can fetch these definitions and use them with OpenAI function calling.
"""

from fastapi import APIRouter

router = APIRouter(tags=["tools"])

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "engram_create_memory",
            "description": "Store a memory for later retrieval. Memories persist across sessions and decay over time based on access patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory content to store. Be specific and include relevant context."
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["working", "episodic", "semantic"],
                        "description": "Memory layer: 'working' for temporary session data, 'episodic' for events/experiences, 'semantic' for facts/knowledge."
                    },
                    "salience": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Importance score 0-1. Higher values decay slower. Default 0.5."
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata about the memory (source, tags, etc)."
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "engram_search_memories",
            "description": "Search stored memories by semantic similarity. Use this to recall relevant past information before responding.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Describe what you're looking for naturally."
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["episodic", "semantic"],
                        "description": "Memory layer to search. 'semantic' for facts, 'episodic' for events."
                    },
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Number of results to return. Default 10."
                    },
                    "min_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Minimum similarity score threshold. Default 0.0."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "engram_list_memories",
            "description": "List recent memories, optionally filtered by layer. Use to review what memories exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "layer": {
                        "type": "string",
                        "enum": ["working", "episodic", "semantic"],
                        "description": "Filter by memory layer."
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                        "description": "Maximum number of results. Default 50."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "engram_get_memory",
            "description": "Get a specific memory by its ID. Use after listing or searching to get full details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The UUID of the memory to retrieve."
                    }
                },
                "required": ["memory_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "engram_delete_memory",
            "description": "Delete a memory by its ID. Use to remove incorrect or outdated memories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The UUID of the memory to delete."
                    }
                },
                "required": ["memory_id"]
            }
        }
    }
]


@router.get("/tools")
async def get_tool_definitions():
    """Return OpenAI-compatible tool definitions for ENGRAM.

    Use these definitions with OpenAI's function calling API to let
    agents interact with ENGRAM memory.
    """
    return {"tools": TOOL_DEFINITIONS}
