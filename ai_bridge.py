# -*- coding: utf-8 -*-
"""GK AI STUDIO - Intel Arc / IPEX-LLM API bridge.

Bu servis 127.0.0.1:11434 üzerinde Ollama'nın temel HTTP yüzünü taklit eder
ve istekleri doğrudan IPEX llama.cpp runner'ına (59584) aktarır.

Amaç: app.py değişmeden çalışmak.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

BRIDGE_HOST = os.environ.get("GK_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("GK_BRIDGE_PORT", "11434"))
RUNNER_URL = os.environ.get("GK_IPEX_RUNNER_URL", "http://127.0.0.1:59584")
DEFAULT_MODEL = os.environ.get("GK_IPEX_MODEL", "qwen2.5-coder:7b")
DEFAULT_CTX = int(os.environ.get("GK_IPEX_CTX", "4096"))
DEFAULT_N_PREDICT = int(os.environ.get("GK_IPEX_N_PREDICT", "512"))
REQUEST_TIMEOUT = int(os.environ.get("GK_IPEX_TIMEOUT", "900"))

# Runner --parallel 1 ile başlatıldı; aynı anda birden fazla inference göndermiyoruz.
INFERENCE_LOCK = threading.Lock()


class BridgeError(RuntimeError):
    pass


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _http_json(url: str, payload: dict[str, Any], timeout: int = REQUEST_TIMEOUT):
    body = _json_bytes(payload)
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BridgeError(f"Runner HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise BridgeError(f"Runner bağlantı hatası: {exc}") from exc


def _runner_health() -> bool:
    try:
        with urllib.request.urlopen(f"{RUNNER_URL}/health", timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            return resp.status == 200 and data.get("status") == 0 and data.get("progress") == 1
    except Exception:
        return False


def _content_from_messages(messages: list[dict[str, Any]]) -> str:
    """Qwen2.5 için temel chat-template metni üretir.

    Runner düşük seviyeli /completion API kullandığı için Ollama'nın mesaj
    nesnelerini doğrudan değil, modelin chat token düzenine yakın biçimde
    tek prompt haline getiriyoruz.
    """
    blocks: list[str] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = message.get("content", "")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            content = "\n".join(parts)
        blocks.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    blocks.append("<|im_start|>assistant\n")
    return "\n".join(blocks)


def _build_prompt_for_generate(data: dict[str, Any]) -> str:
    prompt = data.get("prompt", "")
    system = data.get("system", "")
    if system:
        return f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    return prompt


def _completion_request(prompt: str, options: dict[str, Any] | None, stream: bool):
    options = options or {}
    payload = {
        "prompt": prompt,
        "stream": bool(stream),
        "n_predict": int(options.get("num_predict", DEFAULT_N_PREDICT)),
        "temperature": float(options.get("temperature", 0.2)),
        "top_k": int(options.get("top_k", 40)),
        "top_p": float(options.get("top_p", 0.95)),
        "ctx_size": int(options.get("num_ctx", DEFAULT_CTX)),
    }
    return payload


def _iter_runner_completion(payload: dict[str, Any]):
    body = _json_bytes(payload)
    req = urllib.request.Request(
        f"{RUNNER_URL}/completion",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            while True:
                line = resp.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    continue
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BridgeError(f"Runner HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise BridgeError(f"Runner bağlantı hatası: {exc}") from exc


def _collect_completion(prompt: str, options: dict[str, Any] | None):
    payload = _completion_request(prompt, options, stream=False)
    parts: list[str] = []
    final: dict[str, Any] = {}
    with INFERENCE_LOCK:
        for chunk in _iter_runner_completion(payload):
            content = chunk.get("content", "")
            if content:
                parts.append(content)
            final = chunk
            if chunk.get("done") is True:
                break
    return "".join(parts), final


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "GK-AI-Bridge/0.1"

    def log_message(self, fmt: str, *args):
        print(f"[BRIDGE] {self.address_string()} - {fmt % args}", flush=True)

    def _send_json(self, obj: Any, status: int = 200):
        raw = _json_bytes(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_ndjson(self, lines: list[dict[str, Any]], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        for item in lines:
            self.wfile.write(_json_bytes(item) + b"\n")
            self.wfile.flush()

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8", errors="replace"))

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if path == "/api/version":
            return self._send_json({"version": "0.1-gk-ipex-bridge"})

        if path == "/api/tags":
            return self._send_json({
                "models": [{
                    "name": DEFAULT_MODEL,
                    "model": DEFAULT_MODEL,
                    "modified_at": now,
                    "size": 0,
                    "digest": "ipex-runner-local",
                    "details": {"family": "qwen2.5", "parameter_size": "7B", "quantization_level": "Q4_K_M"},
                }]
            })

        if path == "/api/ps":
            if _runner_health():
                return self._send_json({
                    "models": [{
                        "name": DEFAULT_MODEL,
                        "model": DEFAULT_MODEL,
                        "size": 0,
                        "digest": "ipex-runner-local",
                        "details": {"backend": "sycl", "device": "Intel Arc 140V", "port": 59584},
                    }]
                })
            return self._send_json({"models": []})

        if path == "/health":
            return self._send_json({"status": "ok", "runner": _runner_health()})

        return self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            data = self._read_json()
        except Exception as exc:
            return self._send_json({"error": f"Geçersiz JSON: {exc}"}, 400)

        if path == "/api/generate":
            return self._handle_generate(data)
        if path == "/api/chat":
            return self._handle_chat(data)
        if path == "/api/embeddings":
            return self._send_json({
                "error": "IPEX bridge embedding endpoint bu sürümde henüz uygulanmadı. RAG/embedding ayrı aşamada eklenecek."
            }, 501)

        return self._send_json({"error": "not found"}, 404)

    def _handle_generate(self, data: dict[str, Any]):
        model = data.get("model") or DEFAULT_MODEL
        prompt = _build_prompt_for_generate(data)
        stream = bool(data.get("stream", True))
        options = data.get("options") or {}
        try:
            with INFERENCE_LOCK:
                chunks = list(_iter_runner_completion(_completion_request(prompt, options, stream=True)))
        except BridgeError as exc:
            return self._send_json({"error": str(exc)}, 502)

        text = "".join(c.get("content", "") for c in chunks)
        final = chunks[-1] if chunks else {}
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if not stream:
            return self._send_json({
                "model": model,
                "created_at": created,
                "response": text,
                "done": True,
                "done_reason": final.get("done_reason", "stop"),
                "eval_count": final.get("eval_count", 0),
                "eval_duration": final.get("eval_duration", 0),
            })

        lines = []
        for c in chunks:
            content = c.get("content", "")
            if content:
                lines.append({"model": model, "created_at": created, "response": content, "done": False})
        lines.append({
            "model": model,
            "created_at": created,
            "response": "",
            "done": True,
            "done_reason": final.get("done_reason", "stop"),
            "eval_count": final.get("eval_count", 0),
            "eval_duration": final.get("eval_duration", 0),
        })
        return self._send_ndjson(lines)

    def _handle_chat(self, data: dict[str, Any]):
        model = data.get("model") or DEFAULT_MODEL
        messages = data.get("messages") or []
        prompt = _content_from_messages(messages)
        stream = bool(data.get("stream", True))
        options = data.get("options") or {}

        try:
            with INFERENCE_LOCK:
                chunks = list(_iter_runner_completion(_completion_request(prompt, options, stream=True)))
        except BridgeError as exc:
            return self._send_json({"error": str(exc)}, 502)

        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        final = chunks[-1] if chunks else {}

        if not stream:
            text = "".join(c.get("content", "") for c in chunks)
            return self._send_json({
                "model": model,
                "created_at": created,
                "message": {"role": "assistant", "content": text},
                "done": True,
                "done_reason": final.get("done_reason", "stop"),
                "eval_count": final.get("eval_count", 0),
                "eval_duration": final.get("eval_duration", 0),
            })

        lines = []
        for c in chunks:
            content = c.get("content", "")
            if content:
                lines.append({
                    "model": model,
                    "created_at": created,
                    "message": {"role": "assistant", "content": content},
                    "done": False,
                })
        lines.append({
            "model": model,
            "created_at": created,
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": final.get("done_reason", "stop"),
            "eval_count": final.get("eval_count", 0),
            "eval_duration": final.get("eval_duration", 0),
        })
        return self._send_ndjson(lines)


def main():
    print("=" * 60)
    print("GK AI STUDIO - INTEL ARC IPEX BRIDGE")
    print(f"Bridge : http://{BRIDGE_HOST}:{BRIDGE_PORT}")
    print(f"Runner : {RUNNER_URL}")
    print(f"Model  : {DEFAULT_MODEL}")
    print("=" * 60)
    if _runner_health():
        print("[OK] IPEX runner hazır.")
    else:
        print("[UYARI] IPEX runner hazır değil. Bridge yine açılıyor.")

    server = ThreadingHTTPServer((BRIDGE_HOST, BRIDGE_PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BRIDGE] Kapatılıyor...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
