# C:\AI_YEREL\AI_ES6_YEREL_STUDYO\orchestrator.py
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import time
import threading
import urllib.request
import json

# Windows konsolunda UTF-8 cıktısını zorla
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

COLOR_GPU = "\033[92m[GPU RUNNER]\033[0m"
COLOR_BRIDGE = "\033[94m[AI BRIDGE]\033[0m"
COLOR_STUDIO = "\033[93m[GK STUDIO]\033[0m"
COLOR_SYS = "\033[95m[SYSTEM]\033[0m"

def stream_log(process, prefix):
    for line in iter(process.stdout.readline, ''):
        if line:
            print(f"{prefix} {line.strip()}", flush=True)

def main():
    print(f"{COLOR_SYS} GK AI STUDIO - Intel Arc 140V Orkestrator Baslatiliyor...", flush=True)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["OLLAMA_NUM_GPU"] = "999"
    env["ONEAPI_DEVICE_SELECTOR"] = "level_zero:0"
    env["ZES_ENABLE_SYSMAN"] = "1"
    env["SYCL_CACHE_PERSISTENT"] = "1"
    env["OLLAMA_FLASH_ATTENTION"] = "false"
    env["NO_PROXY"] = "localhost,127.0.0.1"

    ipex_dir = r"C:\AI_IPEX\Ollama\portable"
    runner_exe = os.path.join(ipex_dir, "ollama-lib.exe")
    model_path = r"C:\Users\karye\.ollama\models\blobs\sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463"

    runner_cmd = [
        runner_exe, "runner",
        "--model", model_path,
        "--ctx-size", "32768",
        "--batch-size", "512",
        "--n-gpu-layers", "999",
        "--threads", "4",
        "--no-mmap",
        "--parallel", "1",
        "--port", "59584",
        "--verbose"
    ]

    print(f"{COLOR_SYS} [1/3] IPEX GPU Runner baslatiliyor (Port 59584 / 32K Context)...", flush=True)
    p_runner = subprocess.Popen(
        runner_cmd,
        cwd=ipex_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )
    t_runner = threading.Thread(target=stream_log, args=(p_runner, COLOR_GPU), daemon=True)
    t_runner.start()

    print(f"{COLOR_SYS} Runner yuklenmesi bekleniyor (30 sn limit)...", flush=True)
    ready = False
    for _ in range(30):
        try:
            req = urllib.request.Request("http://127.0.0.1:59584/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == 0 and data.get("progress") == 1:
                    ready = True
                    break
        except Exception:
            pass
        time.sleep(1)

    if not ready:
        print(f"{COLOR_SYS} [HATA] IPEX Runner 30 saniye icinde yanit vermedi.", flush=True)
        p_runner.kill()
        sys.exit(1)

    print(f"{COLOR_SYS} [OK] IPEX Runner hazir: 127.0.0.1:59584", flush=True)

    # 2. AI Bridge
    print(f"{COLOR_SYS} [2/3] AI Bridge baslatiliyor (Port 11434)...", flush=True)
    p_bridge = subprocess.Popen(
        [sys.executable, "ai_bridge.py"],
        cwd=r"C:\AI_YEREL\AI_ES6_YEREL_STUDYO",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )
    t_bridge = threading.Thread(target=stream_log, args=(p_bridge, COLOR_BRIDGE), daemon=True)
    t_bridge.start()

    # 3. Flask App
    print(f"{COLOR_SYS} [3/3] GK AI STUDIO (app.py) baslatiliyor...", flush=True)
    p_studio = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=r"C:\AI_YEREL\AI_ES6_YEREL_STUDYO",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )
    t_studio = threading.Thread(target=stream_log, args=(p_studio, COLOR_STUDIO), daemon=True)
    t_studio.start()

    print(f"{COLOR_SYS} ========================================================", flush=True)
    print(f"{COLOR_SYS} SISTEM HAZIR! Web Arayuz: http://127.0.0.1:5000", flush=True)
    print(f"{COLOR_SYS} ========================================================", flush=True)

    try:
        p_studio.wait()
    except KeyboardInterrupt:
        print(f"\n{COLOR_SYS} Kapatiliyor...", flush=True)
    finally:
        p_studio.kill()
        p_bridge.kill()
        p_runner.kill()

if __name__ == "__main__":
    main()