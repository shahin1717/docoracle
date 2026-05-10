import subprocess
import requests
import json
from dataclasses import dataclass


OLLAMA_URL = "http://localhost:11434"

# Model catalog — ordered best to worst quality
# Each entry: (ollama_name, required_vram_gb, required_ram_gb, description)
LLM_MODELS = [
    ("mistral:7b-instruct-q8_0",    7.0, 8,  "Best quality — needs 7GB VRAM"),
    ("mistral:7b-instruct-q4_0",    4.5, 8,  "Good quality — needs 4.5GB VRAM"),
    ("llama3.2:3b-instruct-q8_0",   3.5, 6,  "Fast + good — needs 3.5GB VRAM"),
    ("llama3.2:3b",                 2.5, 4,  "Fast — needs 2.5GB VRAM"),
    ("phi3:mini",                   2.0, 4,  "Light — needs 2GB VRAM"),
    ("tinyllama:1.1b",              1.0, 2,  "Minimal — needs 1GB VRAM"),
]

EMBED_MODELS = [
    ("nomic-embed-text",  0.5, 2, "Best embedding quality"),
    ("all-minilm",        0.2, 1, "Lightweight embeddings"),
]


@dataclass
class HardwareInfo:
    gpu_name:     str
    gpu_vram_gb:  float
    ram_gb:       float
    has_gpu:      bool
    cuda_version: str


@dataclass 
class ModelRecommendation:
    llm_model:   str
    embed_model: str
    reason:      str
    hardware:    HardwareInfo


def get_hardware_info() -> HardwareInfo:
    """Detect GPU and RAM."""
    gpu_name     = "No GPU"
    gpu_vram_gb  = 0.0
    has_gpu      = False
    cuda_version = "N/A"

    # ── try nvidia-smi ────────────────────────────────────────
    try:
        result = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            line = result.stdout.strip().split("\n")[0]
            parts = line.split(",")
            gpu_name    = parts[0].strip()
            gpu_vram_gb = round(int(parts[1].strip()) / 1024, 1)
            has_gpu     = True

        # cuda version
        ver_result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if ver_result.returncode == 0:
            cuda_version = ver_result.stdout.strip()

    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # ── RAM ───────────────────────────────────────────────────
    ram_gb = 8.0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    ram_kb = int(line.split()[1])
                    ram_gb = round(ram_kb / 1024 / 1024, 1)
                    break
    except Exception:
        try:
            import os
            ram_gb = round(os.sysconf("SC_PAGE_SIZE") *
                          os.sysconf("SC_PHYS_PAGES") / 1024**3, 1)
        except Exception:
            pass

    return HardwareInfo(
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram_gb,
        ram_gb=ram_gb,
        has_gpu=has_gpu,
        cuda_version=cuda_version,
    )


def get_available_ollama_models() -> list[str]:
    """Return list of models already pulled in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


def recommend_models(hw: HardwareInfo) -> ModelRecommendation:
    """Pick best LLM and embedding model based on hardware."""
    available = get_available_ollama_models()

    # ── pick LLM ──────────────────────────────────────────────
    best_llm = None
    reason   = ""

    for model_name, req_vram, req_ram, desc in LLM_MODELS:
        fits_gpu = hw.has_gpu and hw.gpu_vram_gb >= req_vram
        fits_ram = hw.ram_gb >= req_ram

        if fits_gpu and fits_ram:
            best_llm = model_name
            reason   = f"{desc} — your {hw.gpu_name} has {hw.gpu_vram_gb}GB VRAM"
            break
        elif not hw.has_gpu and fits_ram:
            # CPU fallback
            best_llm = model_name
            reason   = f"{desc} — running on CPU (no GPU detected)"
            break

    if not best_llm:
        best_llm = "tinyllama:1.1b"
        reason   = "Minimal model — very limited hardware detected"

    # ── pick embedding ────────────────────────────────────────
    best_embed = "nomic-embed-text"
    for model_name, req_vram, req_ram, _ in EMBED_MODELS:
        if hw.has_gpu and hw.gpu_vram_gb >= req_vram:
            best_embed = model_name
            break

    return ModelRecommendation(
        llm_model=best_llm,
        embed_model=best_embed,
        reason=reason,
        hardware=hw,
    )


def pull_model(model_name: str) -> bool:
    """Pull a model from Ollama registry."""
    print(f"  Pulling {model_name}...")
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            timeout=600
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  Failed: {e}")
        return False


def select_model_interactive() -> ModelRecommendation:
    """
    Full interactive model selection:
    1. Detect hardware
    2. Show recommendation
    3. Let user pick differently if they want
    """
    print("\n" + "=" * 55)
    print("  DocOracle — Model Selection")
    print("=" * 55)

    # ── hardware detection ────────────────────────────────────
    print("\n🔍 Detecting hardware...")
    hw = get_hardware_info()

    if hw.has_gpu:
        print(f"  GPU : {hw.gpu_name}")
        print(f"  VRAM: {hw.gpu_vram_gb} GB")
    else:
        print("  GPU : Not detected (will use CPU)")
    print(f"  RAM : {hw.ram_gb} GB")

    # ── recommendation ────────────────────────────────────────
    rec = recommend_models(hw)
    available = get_available_ollama_models()

    print(f"\n✅ Recommended LLM   : {rec.llm_model}")
    print(f"   Reason            : {rec.reason}")
    print(f"✅ Recommended Embed : {rec.embed_model}")

    # ── show all options ──────────────────────────────────────
    print("\n📋 All available models:")
    print(f"  {'#':<3} {'Model':<40} {'VRAM':<8} {'Status'}")
    print("  " + "-" * 65)

    for i, (name, vram, ram, desc) in enumerate(LLM_MODELS, 1):
        fits   = (hw.has_gpu and hw.gpu_vram_gb >= vram) or (not hw.has_gpu and hw.ram_gb >= ram)
        pulled = any(name in m for m in available)
        status = "✓ pulled" if pulled else ("✓ fits" if fits else "✗ too large")
        marker = " ◄ recommended" if name == rec.llm_model else ""
        print(f"  {i:<3} {name:<40} {vram:<8} {status}{marker}")

    # ── user choice ───────────────────────────────────────────
    print(f"\n  Press Enter to use recommended ({rec.llm_model})")
    print("  Or enter a number to choose different model:")
    choice = input("  > ").strip()

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(LLM_MODELS):
            chosen_name = LLM_MODELS[idx][0]
            rec = ModelRecommendation(
                llm_model=chosen_name,
                embed_model=rec.embed_model,
                reason="Manually selected",
                hardware=hw,
            )
            print(f"  Selected: {chosen_name}")

    # ── pull if needed ────────────────────────────────────────
    llm_pulled   = any(rec.llm_model   in m for m in available)
    embed_pulled = any(rec.embed_model in m for m in available)

    if not llm_pulled:
        print(f"\n⬇️  Model not found locally. Pull it now? (y/n)")
        if input("  > ").strip().lower() == "y":
            pull_model(rec.llm_model)

    if not embed_pulled:
        print(f"\n⬇️  Embedding model not found. Pull it now? (y/n)")
        if input("  > ").strip().lower() == "y":
            pull_model(rec.embed_model)

    print(f"\n🚀 Using: {rec.llm_model} + {rec.embed_model}\n")
    return rec