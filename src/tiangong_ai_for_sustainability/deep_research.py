"""
High-level helpers for orchestrating OpenAI Deep Research workflows.

This module wraps the OpenAI Responses API (`client.responses.create`) with sane defaults
for the Deep Research guide: https://platform.openai.com/docs/guides/deep-research

Goals
-----
* Provide a small, typed surface that Codex automations can depend on.
* Capture tricky request-shaping details (messages, metadata, tool wiring).
* Offer optional Model Context Protocol (MCP) integration that works with Context
  connectors or any other compatible MCP server.

The module intentionally avoids hitting the network on import so it can be safely
used in tooling without an API key present. Instantiate :class:`DeepResearchClient`
once and reuse it across calls to benefit from HTTP connection pooling inside the
OpenAI SDK.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from openai import OpenAI
from openai.pagination import SyncCursorPage
from openai.resources.responses import Responses
from openai.types.responses import Response, ResponseStreamEvent
from openai.types.responses.response_create_params import ToolChoice
from openai.types.responses.tool_param import Mcp as McpToolParam

from .config import load_secrets

MessageList = List[Dict[str, Any]]

DEFAULT_DEEP_RESEARCH_MODEL = "o4-mini-deep-research"


@dataclass(slots=True)
class ResearchPrompt:
    """
    Container representing the user's request for a Deep Research workflow.

    Parameters
    ----------
    question:
        Main research question posed to the model.
    context:
        Optional extra context that should always accompany the prompt. Useful for
        scoping research to a particular industry, dataset, or policy.
    follow_up_questions:
        Additional prompts that should be answered after the primary question. These are
        appended as numbered subtasks inside the message payload.
    """

    question: str
    context: Optional[str] = None
    follow_up_questions: Sequence[str] = field(default_factory=tuple)

    def to_message_block(self) -> str:
        """Render the prompt as a single text block understood by Deep Research."""
        parts: List[str] = [self.question.strip()]
        if self.context:
            parts.append("\nContext:\n" + self.context.strip())
        if self.follow_up_questions:
            followup_lines = "\n".join(f"{idx + 1}. {item.strip()}" for idx, item in enumerate(self.follow_up_questions))
            parts.append("\nFollow-up Questions:\n" + followup_lines)
        return "\n".join(parts).strip()


@dataclass(slots=True)
class MCPServerConfig:
    """
    Declarative description of an MCP server for Deep Research tool access.

    The OpenAI Responses API expects tool entries shaped like::

        {
            "type": "mcp",
            "server_label": "local-files",
            "server_url": "http://127.0.0.1:3000",
            "server_description": "In-project file browser"
        }

    With optional authorization headers, tool whitelists, or approval gates. This
    dataclass mirrors the schema supported by
    :class:`openai.types.responses.tool_param.Mcp` and provides small affordances for
    Context MCP manifests.
    """

    server_label: str
    server_url: str
    server_description: Optional[str] = None
    authorization: Optional[str] = None
    connector_id: Optional[str] = None
    allowed_tools: Optional[Sequence[str]] = None
    require_manual_approval: bool = False
    custom_headers: Mapping[str, str] | None = None

    def to_tool_param(self) -> McpToolParam:
        """
        Convert the config into the structured object accepted by the OpenAI SDK.

        Returns
        -------
        openai.types.responses.tool_param.Mcp
        """

        data: Dict[str, Any] = {
            "type": "mcp",
            "server_label": self.server_label,
            "server_url": self.server_url,
        }
        if self.server_description:
            data["server_description"] = self.server_description
        if self.authorization:
            data["authorization"] = self.authorization
        if self.connector_id:
            data["connector_id"] = self.connector_id
        if self.allowed_tools:
            data["allowed_tools"] = list(self.allowed_tools)
        if self.require_manual_approval:
            raise ValueError("Deep Research requires MCP servers to set require_approval='never'. Disable manual approvals.")
        data["require_approval"] = "never"
        if self.custom_headers:
            data["headers"] = dict(self.custom_headers)
        return McpToolParam(**data)  # type: ignore[arg-type]


@dataclass(slots=True)
class FileSearchConfig:
    """
    Declarative wrapper for the Deep Research file search tool.

    Parameters
    ----------
    vector_store_ids:
        Identifiers of vector stores that should be queryable during the research run.
        Deep Research models currently support up to two vector stores.
    """

    vector_store_ids: Sequence[str]

    def to_tool_param(self) -> Dict[str, Any]:
        """Return the dict structure accepted by the Responses API."""
        if not self.vector_store_ids:
            raise ValueError("FileSearchConfig requires at least one vector_store_id.")
        return {"type": "file_search", "vector_store_ids": list(self.vector_store_ids)}


@dataclass(slots=True)
class CodeInterpreterConfig:
    """
    Configuration for attaching the code interpreter tool to a research run.

    Parameters
    ----------
    container:
        Dict mirrored into the ``container`` field of the tool specification. Use
        ``{'type': 'auto'}`` for the default managed runtime.
    """

    container: Mapping[str, Any] = field(default_factory=lambda: {"type": "auto"})

    def to_tool_param(self) -> Dict[str, Any]:
        """Render the code interpreter configuration into a Responses tool entry."""
        return {"type": "code_interpreter", "container": dict(self.container)}


@dataclass(slots=True)
class DeepResearchConfig:
    """
    Configuration shared across Deep Research requests.

    Attributes
    ----------
    model:
        Responses API model identifier. When omitted, the value is pulled from secrets or
        falls back to :data:`DEFAULT_DEEP_RESEARCH_MODEL`.
    max_output_tokens:
        Optional hard cap on generated tokens. Useful for scripts that need to control
        cost and output size.
    temperature:
        Creativity parameter mirrored from the Responses API. Defaults to API behaviour.
    default_reasoning_effort:
        Optional value for ``reasoning={'effort': ...}``. The Deep Research guide typically
        uses ``'medium'`` or ``'high'``. Set to ``None`` to omit.
    enable_background_mode:
        Set ``True`` to request asynchronous, long-running jobs. The caller is surfaced the
        job id and can poll later with :meth:`DeepResearchClient.retrieve`.
    default_web_search:
        Controls whether the helper auto-injects the ``web_search_preview`` tool when the
        caller does not specify another data source.
    default_file_searches:
        File search tool definitions that should be attached to every request, typically
        for organisation-wide vector stores.
    default_code_interpreter:
        Optional code interpreter configuration applied to each run unless overridden.
    max_tool_calls:
        Optional upper limit for the total number of tool invocations the agent may
        perform.
    """

    model: Optional[str] = None
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    default_reasoning_effort: Optional[str] = "medium"
    enable_background_mode: bool = False
    default_web_search: bool = True
    default_file_searches: Sequence[FileSearchConfig] = field(default_factory=tuple)
    default_code_interpreter: Optional[CodeInterpreterConfig] = None
    max_tool_calls: Optional[int] = None


class DeepResearchClient:
    """
    Facade wrapping :class:`openai.resources.responses.Responses` with Deep Research defaults.

    Examples
    --------
    >>> from tiangong_ai_for_sustainability import DeepResearchClient, ResearchPrompt
    >>> client = DeepResearchClient()
    >>> prompt = ResearchPrompt(question=\"\"\"How can AI optimise solar farm maintenance?\"\"\")
    >>> result = client.run(prompt)
    >>> print(result.output_text)
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        config: DeepResearchConfig | None = None,
        client: Optional[OpenAI] = None,
    ) -> None:
        secrets = load_secrets()
        self.config = config or DeepResearchConfig()

        if not self.config.model:
            self.config.model = secrets.openai.resolve_deep_research_model() or DEFAULT_DEEP_RESEARCH_MODEL

        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or secrets.openai.api_key

        if client is not None:
            self._client = client
        else:
            client_kwargs: Dict[str, Any] = {}
            if resolved_api_key:
                client_kwargs["api_key"] = resolved_api_key
            if organization:
                client_kwargs["organization"] = organization
            self._client = OpenAI(**client_kwargs)

        self._secrets = secrets

    @property
    def responses(self) -> Responses:
        """Expose the underlying Responses resource for advanced scenarios."""
        return self._client.responses

    def run(
        self,
        prompt: ResearchPrompt | str,
        *,
        instructions: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        tags: Optional[Sequence[str]] = None,
        mcp_servers: Optional[Iterable[MCPServerConfig]] = None,
        file_searches: Optional[Iterable[FileSearchConfig]] = None,
        use_web_search: Optional[bool] = None,
        code_interpreter: bool | CodeInterpreterConfig | None = None,
        tool_choice: ToolChoice | str | None = None,
        stream: bool | None = None,
        include_reasoning: bool = True,
        extra_body: Optional[Dict[str, Any]] = None,
        max_tool_calls: Optional[int] = None,
    ) -> DeepResearchResult:
        """
        Execute a Deep Research request and synchronously wait for completion.

        Parameters
        ----------
        prompt:
            Either a :class:`ResearchPrompt` or plain text string with the question to
            investigate.
        instructions:
            Optional system instructions to further constrain the agent behaviour.
        metadata:
            Dictionary persisted alongside the response (e.g. external run ids).
        tags:
            Convenience wrapper that stores tags inside ``metadata['tags']``.
        mcp_servers:
            Iterable of :class:`MCPServerConfig` instances that should be registered as
            tools. This is the hook for Context MCP connectors.
        file_searches:
            Optional collection of :class:`FileSearchConfig` instances describing vector
            stores that should be queried alongside web research.
        use_web_search:
            Override the default behaviour for adding ``web_search_preview`` as a data
            source. When ``False``, ensure another data source (MCP or file search) is
            provided.
        code_interpreter:
            Pass ``True`` to attach a default :class:`CodeInterpreterConfig`, ``False`` to
            disable any configured interpreter, or supply an explicit configuration.
        tool_choice:
            Override automatic tool invocation decisions (pass ``"auto"`` to reset).
        stream:
            When truthy, the request is sent in streaming mode and the resulting events
            are collected before returning.
        include_reasoning:
            Set ``False`` to strip reasoning traces from the final structured output.
        extra_body:
            Raw dictionary merged into the request body. Enables experimentation with new
            API fields without updating this module.
        max_tool_calls:
            Optional ceiling on the number of tool invocations the agent may attempt.
        """

        resolved_use_web_search = self.config.default_web_search if use_web_search is None else use_web_search
        resolved_file_searches: List[FileSearchConfig] = list(self.config.default_file_searches)
        if file_searches:
            resolved_file_searches.extend(file_searches)
        resolved_code_interpreter = self._resolve_code_interpreter_config(code_interpreter)
        resolved_max_tool_calls = max_tool_calls if max_tool_calls is not None else self.config.max_tool_calls

        body: Dict[str, Any] = self._prepare_request(
            prompt=prompt,
            instructions=instructions,
            metadata=metadata,
            tags=tags,
            mcp_servers=mcp_servers,
            file_searches=resolved_file_searches,
            use_web_search=resolved_use_web_search,
            code_interpreter=resolved_code_interpreter,
            tool_choice=tool_choice,
            include_reasoning=include_reasoning,
            max_tool_calls=resolved_max_tool_calls,
        )
        if stream:
            response = self.responses.stream(**body, extra_body=extra_body)
            events = list(response)
            latest = response.get_final_response()
            return DeepResearchResult(final_response=latest, stream_events=events)
        job = self.responses.create(**body, extra_body=extra_body)
        return DeepResearchResult(final_response=job, stream_events=None)

    def run_background(
        self,
        prompt: ResearchPrompt | str,
        *,
        instructions: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        tags: Optional[Sequence[str]] = None,
        mcp_servers: Optional[Iterable[MCPServerConfig]] = None,
        file_searches: Optional[Iterable[FileSearchConfig]] = None,
        use_web_search: Optional[bool] = None,
        code_interpreter: bool | CodeInterpreterConfig | None = None,
        max_tool_calls: Optional[int] = None,
    ) -> Response:
        """
        Submit a Deep Research job using background mode and return immediately.

        The caller can use :meth:`retrieve` to poll for completion.
        """

        if not self.config.enable_background_mode:
            raise ValueError("Background mode is disabled. Set config.enable_background_mode=True.")
        resolved_use_web_search = self.config.default_web_search if use_web_search is None else use_web_search
        resolved_file_searches: List[FileSearchConfig] = list(self.config.default_file_searches)
        if file_searches:
            resolved_file_searches.extend(file_searches)
        resolved_code_interpreter = self._resolve_code_interpreter_config(code_interpreter)
        resolved_max_tool_calls = max_tool_calls if max_tool_calls is not None else self.config.max_tool_calls
        body = self._prepare_request(
            prompt=prompt,
            instructions=instructions,
            metadata=metadata,
            tags=tags,
            mcp_servers=mcp_servers,
            file_searches=resolved_file_searches,
            use_web_search=resolved_use_web_search,
            code_interpreter=resolved_code_interpreter,
            include_reasoning=True,
            max_tool_calls=resolved_max_tool_calls,
        )
        body["background"] = True
        return self.responses.create(**body)

    def retrieve(self, response_id: str) -> Response:
        """Fetch a previously created response by id."""
        return self.responses.retrieve(response_id)

    def list(self, *, limit: int = 20, order: str = "desc") -> SyncCursorPage[Response]:
        """List historical responses for bookkeeping and monitoring."""
        return self.responses.list(limit=limit, order=order)

    def cancel(self, response_id: str) -> Response:
        """Cancel a background response that has not finished."""
        return self.responses.cancel(response_id)

    # Internal helpers -----------------------------------------------------------------

    def _prepare_request(
        self,
        *,
        prompt: ResearchPrompt | str,
        instructions: Optional[str],
        metadata: Optional[Mapping[str, Any]],
        tags: Optional[Sequence[str]],
        mcp_servers: Optional[Iterable[MCPServerConfig]],
        file_searches: Sequence[FileSearchConfig],
        use_web_search: bool,
        code_interpreter: Optional[CodeInterpreterConfig],
        tool_choice: ToolChoice | str | None = None,
        include_reasoning: bool = True,
        max_tool_calls: Optional[int] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"model": self.config.model}

        if isinstance(prompt, ResearchPrompt):
            prompt_text = prompt.to_message_block()
        else:
            prompt_text = str(prompt).strip()

        messages: MessageList = [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt_text}],
            }
        ]
        body["input"] = messages

        if instructions:
            body["instructions"] = instructions
        if self.config.max_output_tokens is not None:
            body["max_output_tokens"] = self.config.max_output_tokens
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.default_reasoning_effort:
            body["reasoning"] = {"effort": self.config.default_reasoning_effort}

        merged_metadata: Dict[str, Any] = {}
        if metadata:
            merged_metadata.update(metadata)
        if tags:
            merged_metadata.setdefault("tags", list(tags))
        if merged_metadata:
            body["metadata"] = merged_metadata

        tools: List[Any] = []
        if mcp_servers:
            tools.extend(server.to_tool_param() for server in mcp_servers)
        for file_search in file_searches:
            tools.append(file_search.to_tool_param())
        if use_web_search and not self._has_tool_type(tools, "web_search_preview"):
            tools.append({"type": "web_search_preview"})
        if code_interpreter is not None:
            tools.append(code_interpreter.to_tool_param())
        if not self._includes_data_source(tools):
            raise ValueError("Deep Research requests require at least one data source tool " "(web_search_preview, file_search, or MCP server).")
        if tools:
            body["tools"] = tools
        if tool_choice:
            body["tool_choice"] = tool_choice
        if self.config.enable_background_mode:
            body["background"] = True

        if not include_reasoning:
            body["response_format"] = {"type": "text"}
        if max_tool_calls is not None:
            body["max_tool_calls"] = max_tool_calls
        return body

    def _resolve_code_interpreter_config(
        self,
        override: bool | CodeInterpreterConfig | None,
    ) -> Optional[CodeInterpreterConfig]:
        if isinstance(override, CodeInterpreterConfig):
            return override
        if override is True:
            return self.config.default_code_interpreter or CodeInterpreterConfig()
        if override is False:
            return None
        if override is None:
            return self.config.default_code_interpreter
        raise TypeError("code_interpreter must be bool, None, or CodeInterpreterConfig.")

    @staticmethod
    def _tool_type(tool: Any) -> Optional[str]:
        if isinstance(tool, Mapping):
            return tool.get("type")
        if hasattr(tool, "type"):
            return getattr(tool, "type")
        return None

    def _has_tool_type(self, tools: Sequence[Any], expected_type: str) -> bool:
        return any(self._tool_type(tool) == expected_type for tool in tools)

    def _includes_data_source(self, tools: Sequence[Any]) -> bool:
        for tool in tools:
            tool_type = self._tool_type(tool)
            if tool_type in {"web_search_preview", "file_search", "mcp"}:
                return True
        return False


@dataclass(slots=True)
class DeepResearchResult:
    """
    Wrapper around a Deep Research response for ergonomic downstream consumption.

    Attributes
    ----------
    final_response:
        The terminal :class:`openai.types.responses.Response` object returned by the API.
    stream_events:
        For streaming runs, this captures the entire event list so automations can inspect
        search queries, tool invocations, and reasoning traces.
    """

    final_response: Response
    stream_events: Optional[List[ResponseStreamEvent]]

    @property
    def id(self) -> str:
        """Return the response id."""
        return self.final_response.id

    @property
    def output_text(self) -> str:
        """
        Extract concatenated text outputs from the response.

        Deep Research responses typically contain multiple output blocks; this helper
        flattens them for quick summaries.
        """

        chunks: List[str] = []
        for item in self.final_response.output or []:
            if item.type == "output_text":
                chunks.append(item.text)
            elif item.type == "message":
                contents = getattr(item, "content", None)
                if contents is None and isinstance(item, Mapping):  # type: ignore[arg-type]
                    contents = item.get("content")
                if contents:
                    for entry in contents:
                        text = None
                        if isinstance(entry, Mapping):
                            text = entry.get("text")
                        else:
                            text = getattr(entry, "text", None)
                        if text:
                            chunks.append(text)
        return "\n\n".join(chunk.strip() for chunk in chunks if chunk)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a serialisable dictionary."""
        data = asdict(self)
        data["final_response"] = self.final_response.model_dump()
        if self.stream_events is not None:
            data["stream_events"] = [event.model_dump() for event in self.stream_events]
        return data
