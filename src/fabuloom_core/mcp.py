"""Small stdio MCP adapter over the shared Fabuloom engine.

The adapter deliberately contains protocol translation only. Project storage,
catalog access and jobs remain implemented by :class:`EngineService`, so an
agent calling MCP observes the same state as Desktop, CLI and HTTP clients.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .engine import EngineService
from .paths import FabuloomPaths


SERVER_INFO = {"name": "fabuloom-studio", "version": "0.1.0"}


def tool_definitions() -> list[dict[str, object]]:
    """Return the stable, read/write tool surface exposed to local agents."""

    return [
        {"name": "fabuloom_status", "description": "Read shared engine status.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "fabuloom_projects_list", "description": "List persisted Fabuloom projects.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "fabuloom_project_get", "description": "Read one project by stable ID.", "inputSchema": {"type": "object", "required": ["project_id"], "properties": {"project_id": {"type": "string"}}}},
        {"name": "fabuloom_project_create", "description": "Create a project in the shared project store.", "inputSchema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "project_id": {"type": "string"}, "metadata": {"type": "object"}}}},
        {"name": "fabuloom_project_update", "description": "Update a project with optional optimistic revision checking.", "inputSchema": {"type": "object", "required": ["project_id", "payload"], "properties": {"project_id": {"type": "string"}, "payload": {"type": "object"}, "expected_revision": {"type": "integer"}}}},
        {"name": "fabuloom_library_search", "description": "Search the configured private asset catalog without copying media.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "kind": {"type": "string"}, "missing": {"type": "boolean"}}}},
        {"name": "fabuloom_job_create", "description": "Start a supported shared-engine job.", "inputSchema": {"type": "object", "required": ["kind"], "properties": {"kind": {"type": "string", "enum": ["validate-project", "catalog-scan"]}, "payload": {"type": "object"}}}},
        {"name": "fabuloom_job_get", "description": "Read a persistent job record.", "inputSchema": {"type": "object", "required": ["job_id"], "properties": {"job_id": {"type": "string"}}}},
        {"name": "fabuloom_job_cancel", "description": "Request cancellation of a shared-engine job.", "inputSchema": {"type": "object", "required": ["job_id"], "properties": {"job_id": {"type": "string"}}}},
    ]


def _string(args: dict[str, Any], key: str, *, required: bool = True) -> str:
    value = args.get(key)
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"{key} must be a non-empty string")
    return value


def dispatch_tool(engine: EngineService, name: str, arguments: dict[str, Any] | None = None) -> object:
    """Dispatch one MCP tool to the shared engine without duplicating logic."""

    args = arguments or {}
    if name == "fabuloom_status":
        return engine.status()
    if name == "fabuloom_projects_list":
        return {"format": "fabuloom.projects/0.1", "projects": engine.list_projects()}
    if name == "fabuloom_project_get":
        return engine.get_project(_string(args, "project_id"))
    if name == "fabuloom_project_create":
        project_id = args.get("project_id")
        metadata = args.get("metadata")
        if project_id is not None and not isinstance(project_id, str):
            raise ValueError("project_id must be a string")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        return engine.create_project(_string(args, "name"), project_id=project_id, metadata=metadata)
    if name == "fabuloom_project_update":
        payload = args.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        expected = args.get("expected_revision")
        if expected is not None and (isinstance(expected, bool) or not isinstance(expected, int)):
            raise ValueError("expected_revision must be an integer")
        return engine.update_project(_string(args, "project_id"), payload, expected_revision=expected)
    if name == "fabuloom_library_search":
        query = args.get("query", "")
        kind = args.get("kind")
        missing = args.get("missing")
        if not isinstance(query, str) or (kind is not None and not isinstance(kind, str)) or (missing is not None and not isinstance(missing, bool)):
            raise ValueError("query, kind and missing have invalid types")
        return {"format": "fabuloom.library-search/0.1", "assets": engine.search_library(query, kind=kind, missing=missing)}
    if name == "fabuloom_job_create":
        payload = args.get("payload")
        if payload is not None and not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        return engine.create_job(_string(args, "kind"), payload)
    if name == "fabuloom_job_get":
        return engine.get_job(_string(args, "job_id"))
    if name == "fabuloom_job_cancel":
        return engine.cancel_job(_string(args, "job_id"))
    raise ValueError(f"unknown tool: {name}")


def handle_message(engine: EngineService, message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one newline-delimited JSON-RPC/MCP message."""

    request_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "method is required"}}
    if request_id is None and method.startswith("notifications/"):
        return None
    try:
        params = message.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError("params must be an object")
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}
        elif method == "tools/list":
            result = {"tools": tool_definitions()}
        elif method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str):
                raise ValueError("tool name is required")
            result_value = dispatch_tool(engine, name, params.get("arguments"))
            result = {"content": [{"type": "text", "text": json.dumps(result_value, ensure_ascii=False)}], "structuredContent": result_value}
        else:
            raise ValueError(f"method not found: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": f"{type(exc).__name__}: {exc}"}}


def serve_stdio(engine: EngineService) -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_message(engine, message)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"invalid JSON-RPC message: {exc}"}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    serve_stdio(EngineService(FabuloomPaths.discover(configured_root=args.root)))
    return 0


__all__ = ["dispatch_tool", "handle_message", "main", "serve_stdio", "tool_definitions"]


if __name__ == "__main__":
    raise SystemExit(main())
