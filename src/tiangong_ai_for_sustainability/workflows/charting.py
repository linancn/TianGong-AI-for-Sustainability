"""
Shared helpers for rendering charts via the AntV MCP server.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import httpx

from ..core.logging import get_logger

logger = get_logger(__name__)

def call_chart_tool(endpoint: str, tool_name: str, arguments: Mapping[str, Any]) -> Optional[str]:
    """
    Invoke an MCP chart tool and return the image URL when available.
    """

    logger.debug(
        "Calling MCP chart tool",
        extra={"endpoint": endpoint, "tool_name": tool_name},
    )

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    with httpx.Client(timeout=30.0) as client:
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "clientInfo": {"name": "tiangong-workflow", "version": "0.1.0"},
                "capabilities": {},
            },
        }
        client.post(endpoint, headers=headers, json=init_payload)

        call_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": dict(arguments),
            },
        }
        response = client.post(endpoint, headers=headers, json=call_payload)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("result", {})
        content = result.get("content", [])
        logger.debug(
            "Received MCP chart tool response",
            extra={"endpoint": endpoint, "tool_name": tool_name, "content_items": len(content)},
        )
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "image" and "data" in item:
                data = item["data"]
                if isinstance(data, str) and data.startswith("http"):
                    return data
            if item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text.startswith("http"):
                    return text
        return None


def download_chart_image(url: str, destination: Path) -> bool:
    """
    Download an image from the chart server into ``destination``.
    """

    logger.debug("Downloading chart image", extra={"url": url, "destination": destination.as_posix()})

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
            destination.write_bytes(response.content)
            return True
    except httpx.HTTPError as exc:
        logger.error("Failed to download chart image", extra={"url": url, "error": str(exc)})
        destination.write_text(f"Failed to download chart image: {exc}\n", encoding="utf-8")
        return False


def launch_chart_server() -> Optional[subprocess.Popen[str]]:
    """Launch the AntV MCP chart server via ``npx`` when available."""

    if shutil.which("npx") is None:
        logger.warning("Cannot auto-launch chart server because npx is unavailable")
        return None
    try:
        proc = subprocess.Popen(
            ["npx", "-y", "@antv/mcp-server-chart", "--transport", "streamable"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        logger.info("Launched MCP chart server via npx", extra={"pid": proc.pid if proc else None})
        return proc
    except OSError:
        logger.error("Failed to launch MCP chart server via npx", exc_info=True)
        return None


def ensure_chart_image(
    endpoint: str,
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
    destination: Path,
    auto_launch: bool = True,
    wait_seconds: float = 5.0,
) -> bool:
    """
    Ensure a chart image is written to ``destination`` by calling the MCP server.
    """

    logger.debug(
        "Ensuring chart image",
        extra={"endpoint": endpoint, "tool_name": tool_name, "destination": destination.as_posix()},
    )

    launcher_proc: Optional[subprocess.Popen[str]] = None
    try:
        image_url = call_chart_tool(endpoint, tool_name, arguments)
    except (httpx.HTTPError, ValueError) as exc:
        if auto_launch and ("Connection refused" in str(exc) or isinstance(exc, httpx.ConnectError)):
            launcher_proc = launch_chart_server()
            if launcher_proc is None:
                logger.error("Chart generation failed; auto-launch unavailable", extra={"error": str(exc)})
                destination.write_text(f"Chart generation failed: {exc}\n", encoding="utf-8")
                return False
            time.sleep(wait_seconds)
            try:
                image_url = call_chart_tool(endpoint, tool_name, arguments)
            except Exception as retry_exc:  # pragma: no cover - defensive
                logger.error(
                    "Chart generation failed after retry",
                    extra={"error": str(retry_exc)},
                )
                destination.write_text(f"Chart generation failed after retry: {retry_exc}\n", encoding="utf-8")
                return False
        else:
            logger.error("Chart generation failed", extra={"error": str(exc)})
            destination.write_text(f"Chart generation failed: {exc}\n", encoding="utf-8")
            return False
    finally:
        if launcher_proc is not None:
            launcher_proc.terminate()
            try:
                launcher_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                launcher_proc.kill()

    if not image_url:
        logger.warning("Chart generation returned no image URL")
        destination.write_text("Chart generation returned no image URL.\n", encoding="utf-8")
        return False

    logger.debug("Chart image URL resolved", extra={"url": image_url})
    return download_chart_image(image_url, destination)
