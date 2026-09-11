# C:\AI_YEREL\AI_ES6_YEREL_STUDYO\ai_bridge.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# %100 Yerel Ollama Embedding Modeli
EMBED_MODEL_NAME = "nomic-embed-text"

BRIDGE_HOST = os.environ.get("GK_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("GK_BRIDGE_PORT", "11434"))
RUNNER_URL = os.environ.get("GK_IPEX_RUNNER_URL", "http://127.0.0.1:59584")
DEFAULT_MODEL = os.environ.get("GK_IPEX_MODEL", "qwen2.5-coder:7b")
DEFAULT_CTX = int(os.environ.get("GK_IPEX_CTX", "32768"))
DEFAULT_N_PREDICT = int(os.environ.get("GK_IPEX_N_PREDICT", "2048"))
REQUEST_TIMEOUT = int(os.environ.get("GK_IPEX_TIMEOUT", "300"))

INFERENCE_LOCK = threading.Lock()

def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

def _runner_health() -> bool:
    try:
        req = urllib.request.Request(f"{RUNNER_URL}/health", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            return resp.status == 200 and data.get("status") == 0 and data.get("progress") == 1
    except Exception:
        return False

def _get_installed_models_from_disk() -> list[dict[str, Any]]:
    """Diskteki Ollama manifest klasorunu tarayarak yuklu tum modelleri dinamik listeler."""
    models = []
    user_home = os.path.expanduser("~")
    manifest_base = os.path.join(user_home, ".ollama", "models", "manifests", "registry.ollama.ai", "library")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if os.path.exists(manifest_base):
        for model_folder in os.listdir(manifest_base):
            folder_path = os.path.join(manifest_base, model_folder)
            if os.path.isdir(folder_path):
                for tag_file in os.listdir(folder_path):
                    tag_path = os.path.join(folder_path, tag_file)
                    if os.path.isfile(tag_path):
                        model_name = f"{model_folder}:{tag_file}" if tag_file != "latest" else model_folder
                        models.append({
                            "name": model_name,
                            "model": model_name,
                            "modified_at": now,
                            "size": 4681197056,
                            "digest": "sha256:local",
                            "details": {
                                "parent_model": "",
                                "format": "gguf",
                                "family": model_folder,
                                "families": [model_folder],
                                "parameter_size": "7B",
                                "quantization_level": "Q4_K_M"
                            }
                        })
    if not models:
        models.append({
            "name": DEFAULT_MODEL,
            "model": DEFAULT_MODEL,
            "modified_at": now,
            "size": 4681197056,
            "digest": "sha256:default",
            "details": {"format": "gguf", "family": "qwen2"}
        })
    return models

def _content_from_messages(messages: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"]
            content = "\n".join(parts)
        blocks.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    blocks.append("<|im_start|>assistant\n")
    return "\n".join(blocks)

def _completion_request(prompt: str, options: dict[str, Any] | None, stream: bool):
    options = options or {}
    return {
        "prompt": prompt,
        "stream": bool(stream),
        "n_predict": int(options.get("num_predict", DEFAULT_N_PREDICT)),
        "temperature": float(options.get("temperature", 0.2)),
        "top_k": int(options.get("top_k", 40)),
        "top_p": float(options.get("top_p", 0.95)),
        "ctx_size": int(options.get("num_ctx", DEFAULT_CTX)),
    }

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
    except Exception as exc:
        yield {"error": str(exc), "done": True}

def _get_real_embedding(text: str) -> list[float]:
    """HuggingFace yerine doğrudan yerel Ollama nomic-embed-text modelini çağırır."""
    try:
        payload = _json_bytes({"model": EMBED_MODEL_NAME, "prompt": text})
        req = urllib.request.Request(
            f"{RUNNER_URL}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data.get("embedding", [0.0] * 768)
    except Exception as e:
        print(f"[BRIDGE HATA] Yerel Embedding alinamadi: {e}", flush=True)
        return [0.0] * 768

class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "GK-AI-Bridge/2.0"

    def log_message(self, fmt: str, *args):
        print(f"[BRIDGE] {fmt % args}", flush=True)

    def _send_json(self, obj: Any, status: int = 200):
        raw = _json_bytes(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_ndjson_stream(self, payload: dict[str, Any], model: str):
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        acquired = INFERENCE_LOCK.acquire(timeout=10)
        
        if not acquired:
            err_chunk = {"model": model, "created_at": created, "message": {"role": "assistant", "content": "Sistem meşgul, lütfen tekrar deneyin."}, "done": True}
            self.wfile.write(_json_bytes(err_chunk) + b"\n")
            return

        try:
            for c in _iter_runner_completion(payload):
                content = c.get("content", "")
                done = c.get("done", False)
                if content or done:
                    chunk = {
                        "model": model,
                        "created_at": created,
                        "response": content,
                        "message": {"role": "assistant", "content": content},
                        "done": done
                    }
                    self.wfile.write(_json_bytes(chunk) + b"\n")
                    self.wfile.flush()
                if done:
                    break
        finally:
            INFERENCE_LOCK.release()

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8", errors="replace"))

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path == "/api/version":
            return self._send_json({"version": "0.1.0-ipex-bridge"})

        if path in ("/api/tags", "/api/ps"):
            models = _get_installed_models_from_disk()
            return self._send_json({"models": models})

        if path == "/health":
            return self._send_json({"status": "ok", "runner": _runner_health()})

        return self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            data = self._read_json()
        except Exception as exc:
            return self._send_json({"error": f"Gecersiz JSON: {exc}"}, 400)

        if path == "/api/generate":
            return self._handle_generate(data)
        if path == "/api/chat":
            return self._handle_chat(data)
        if path in ("/api/embeddings", "/api/embed"):
            return self._handle_embeddings(data)

        return self._send_json({"error": "not found"}, 404)

    def _handle_embeddings(self, data: dict[str, Any]):
        prompt = data.get("prompt") or data.get("input") or ""
        if isinstance(prompt, list):
            prompt = " ".join(prompt)
        embedding = _get_real_embedding(str(prompt))
        return self._send_json({
            "embedding": embedding,
            "embeddings": [embedding]
        })

    def _handle_generate(self, data: dict[str, Any]):
        model = data.get("model") or DEFAULT_MODEL
        prompt = data.get("prompt", "")
        system = data.get("system", "")
        if system:
            prompt = f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        options = data.get("options") or {}
        payload = _completion_request(prompt, options, stream=True)
        return self._send_ndjson_stream(payload, model)

    def _handle_chat(self, data: dict[str, Any]):
        model = data.get("model") or DEFAULT_MODEL
        messages = data.get("messages") or []
        prompt = _content_from_messages(messages)
        options = data.get("options") or {}
        payload = _completion_request(prompt, options, stream=True)
        return self._send_ndjson_stream(payload, model)

def main():
    print(f"[BRIDGE] Baslatiliyor -> http://{BRIDGE_HOST}:{BRIDGE_PORT} | Runner -> {RUNNER_URL}", flush=True)
    print(f"[BRIDGE] Yerel Embedding Modeli Aktif: {EMBED_MODEL_NAME}", flush=True)
    server = ThreadingHTTPServer((BRIDGE_HOST, BRIDGE_PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()