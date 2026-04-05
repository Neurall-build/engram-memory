#!/usr/bin/env python3
# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""ENGRAM skill handler for OpenClaw.

Processes @engram commands and communicates with the ENGRAM REST API.
"""

import argparse
import json
import os
import sys

import requests


def load_config():
    """Load skill configuration."""
    config = {
        "server_url": os.environ.get("ENGRAM_SERVER_URL", "http://127.0.0.1:8000"),
        "api_key": os.environ.get("ENGRAM_API_KEY", ""),
        "user_id": os.environ.get("ENGRAM_USER_ID", "default"),
        "default_layer": os.environ.get("ENGRAM_DEFAULT_LAYER", "episodic"),
    }
    return config


def get_headers(config):
    """Get request headers with optional auth."""
    headers = {"Content-Type": "application/json"}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"
    return headers


def cmd_remember(args, config):
    """Store a memory."""
    content = " ".join(args.content)
    payload = {
        "content": content,
        "user_id": config["user_id"],
        "layer": args.layer or config["default_layer"],
        "salience": args.salience,
    }
    if args.metadata:
        payload["metadata"] = json.loads(args.metadata)

    resp = requests.post(
        f"{config['server_url']}/v1/memories",
        json=payload,
        headers=get_headers(config),
    )

    if resp.status_code == 201:
        data = resp.json()
        return f"Memory stored (id: {data['id']}, layer: {data['layer']}, salience: {data['salience']})"
    else:
        return f"Error storing memory: {resp.status_code} - {resp.text}"


def cmd_recall(args, config):
    """Search memories."""
    query = " ".join(args.query)
    payload = {
        "query": query,
        "user_id": config["user_id"],
        "layer": args.layer or "semantic",
        "top_k": args.top_k,
    }

    resp = requests.post(
        f"{config['server_url']}/v1/memories/search",
        json=payload,
        headers=get_headers(config),
    )

    if resp.status_code == 200:
        data = resp.json()
        if not data.get("data"):
            return "No memories found matching your query."
        results = []
        for item in data["data"]:
            mem = item["memory"]
            score = item.get("score", 0)
            results.append(f"[{score:.2f}] {mem['content']} (id: {mem['id']})")
        return "\n".join(results)
    else:
        return f"Error searching memories: {resp.status_code} - {resp.text}"


def cmd_list(args, config):
    """List recent memories."""
    params = {
        "user_id": config["user_id"],
        "layer": args.layer or config["default_layer"],
        "limit": args.limit,
    }

    resp = requests.get(
        f"{config['server_url']}/v1/memories",
        params=params,
        headers=get_headers(config),
    )

    if resp.status_code == 200:
        data = resp.json()
        if not data.get("data"):
            return "No memories found."
        results = []
        for mem in data["data"]:
            results.append(f"- {mem['content']} (id: {mem['id']}, layer: {mem['layer']})")
        return f"Found {data['total']} memories:\n" + "\n".join(results)
    else:
        return f"Error listing memories: {resp.status_code} - {resp.text}"


def cmd_forget(args, config):
    """Delete a memory."""
    mem_id = args.memory_id

    resp = requests.delete(
        f"{config['server_url']}/v1/memories/{mem_id}",
        headers=get_headers(config),
    )

    if resp.status_code == 204:
        return f"Memory {mem_id} deleted."
    else:
        return f"Error deleting memory: {resp.status_code} - {resp.text}"


def main():
    """Main entry point for the ENGRAM skill."""
    parser = argparse.ArgumentParser(description="ENGRAM memory skill for OpenClaw")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # remember command
    remember_parser = subparsers.add_parser("remember", help="Store a memory")
    remember_parser.add_argument("content", nargs="+", help="Memory content")
    remember_parser.add_argument("--layer", choices=["working", "episodic", "semantic"], default=None)
    remember_parser.add_argument("--salience", type=float, default=0.5)
    remember_parser.add_argument("--metadata", default=None)

    # recall command
    recall_parser = subparsers.add_parser("recall", help="Search memories")
    recall_parser.add_argument("query", nargs="+", help="Search query")
    recall_parser.add_argument("--layer", choices=["episodic", "semantic"], default=None)
    recall_parser.add_argument("--top_k", type=int, default=10)

    # list command
    list_parser = subparsers.add_parser("list", help="List memories")
    list_parser.add_argument("--layer", choices=["working", "episodic", "semantic"], default=None)
    list_parser.add_argument("--limit", type=int, default=50)

    # forget command
    forget_parser = subparsers.add_parser("forget", help="Delete a memory")
    forget_parser.add_argument("memory_id", help="Memory ID to delete")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config()

    commands = {
        "remember": cmd_remember,
        "recall": cmd_recall,
        "list": cmd_list,
        "forget": cmd_forget,
    }

    result = commands[args.command](args, config)
    print(result)


if __name__ == "__main__":
    main()
