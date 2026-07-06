"""Minimal Gemini backend matching OpenAIModel.query (vision + tools, non-stream).

Stateless: converts the full message list to Gemini Content each call. Handles
mini-articraft's message shapes: system, user (str or [text/image blocks]),
assistant (content + tool_calls[{id,name,arguments}]), and function_call_output items.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any


class GeminiModel:
    # thinking budgets per level (matches actant's reference config)
    THINKING_BUDGETS = {"none": 0, "low": 4096, "med": 8192, "high": 24576}

    def __init__(self, model_id: str | None = None, thinking_level: str = "high"):
        from google import genai
        self.model_id = model_id or os.environ.get("MINI_ARTICRAFT_GEMINI_MODEL", "gemini-3.5-flash")
        self.thinking_budget = self.THINKING_BUDGETS.get(thinking_level, 8192)
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    async def query(self, messages: list[dict[str, Any]], *, tools: list[dict] | None = None) -> dict:
        from google.genai import types
        system = "\n\n".join(
            m["content"] for m in messages
            if m.get("role") == "system" and "type" not in m and isinstance(m.get("content"), str))
        contents = self._convert(messages)
        decls = [self._tool(t) for t in (tools or [])]
        cfg = types.GenerateContentConfig(
            system_instruction=system or None,
            tools=[types.Tool(function_declarations=decls)] if decls else None,
            temperature=1.0,
            # explicit positive budget + include_thoughts (actant reference); the
            # thought_signature on function calls is captured + round-tripped below
            thinking_config=types.ThinkingConfig(
                thinking_budget=self.thinking_budget, include_thoughts=self.thinking_budget > 0),
        )
        resp = await self.client.aio.models.generate_content(
            model=self.model_id, contents=contents, config=cfg)
        text, calls = "", []
        thinking = ""
        for cand in (resp.candidates or []):
            for part in (cand.content.parts if cand.content else []) or []:
                if getattr(part, "thought", False):
                    # thought SUMMARIES are display-only (context state rides
                    # the thought_signature on function calls) - keep for trace
                    if getattr(part, "text", None):
                        thinking += part.text
                    continue
                if getattr(part, "text", None):
                    text += part.text
                fc = getattr(part, "function_call", None)
                if fc:
                    sig = getattr(part, "thought_signature", None)
                    calls.append({"id": f"{fc.name}_{len(calls)}", "name": fc.name,
                                  "arguments": json.dumps(dict(fc.args or {})),
                                  "thought_signature": base64.b64encode(sig).decode() if sig else None})
        usage = getattr(resp, "usage_metadata", None)
        tok = {"total_tokens": int(getattr(usage, "total_token_count", 0) or 0)} if usage else {}
        return {"text": text, "thinking": thinking, "tool_calls": calls, "token_usage": tok, "cost": 0.0}

    async def close(self) -> None:
        return None

    # ---- conversion ----
    @staticmethod
    def _clean_schema(node):
        """Strip OpenAI-only keys Gemini rejects (additionalProperties), recursively."""
        if isinstance(node, dict):
            return {k: GeminiModel._clean_schema(v) for k, v in node.items()
                    if k not in ("additionalProperties",)}
        if isinstance(node, list):
            return [GeminiModel._clean_schema(v) for v in node]
        return node

    def _tool(self, tool: dict):
        from google.genai import types
        params = self._clean_schema(dict(tool.get("parameters", {})))
        return types.FunctionDeclaration(name=tool["name"],
                                         description=tool.get("description", ""),
                                         parameters=params)

    def _blocks(self, content):
        from google.genai import types
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(types.Part(text=b))
            elif b.get("type") == "text":
                parts.append(types.Part(text=b["text"]))
            elif b.get("type") == "image":
                s = b.get("source", {})
                if s.get("type") == "base64":
                    parts.append(types.Part(inline_data=types.Blob(
                        mime_type=s.get("media_type", "image/png"),
                        data=base64.b64decode(s["data"]))))
        return parts

    def _convert(self, messages):
        from google.genai import types
        id2name = {}
        for m in messages:
            for tc in (m.get("tool_calls") or []):
                id2name[tc["id"]] = tc["name"]
        contents = []
        for m in messages:
            if m.get("role") == "system" and "type" not in m:
                continue
            if m.get("type") == "function_call_output":
                try:
                    body = json.loads(m.get("output") or "{}")
                except (TypeError, ValueError):
                    body = {"result": m.get("output")}
                contents.append(types.Content(role="user", parts=[types.Part(
                    function_response=types.FunctionResponse(
                        name=id2name.get(m.get("call_id"), "tool"), response=body))]))
                continue
            role = "model" if m.get("role") == "assistant" else "user"
            parts = []
            content = m.get("content")
            if isinstance(content, list):
                parts.extend(self._blocks(content))
            elif content:
                parts.append(types.Part(text=content))
            for tc in (m.get("tool_calls") or []):
                try:
                    args = json.loads(tc.get("arguments") or "{}")
                except (TypeError, ValueError):
                    args = {}
                sig = tc.get("thought_signature")
                parts.append(types.Part(
                    function_call=types.FunctionCall(name=tc["name"], args=args),
                    thought_signature=base64.b64decode(sig) if sig else None))
            if not parts:
                parts = [types.Part(text="")]
            contents.append(types.Content(role=role, parts=parts))
        return contents
