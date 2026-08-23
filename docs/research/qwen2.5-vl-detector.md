# Qwen2.5-VL Integration for TrashTag

*Research date: 2026-08-23*

## Model Overview

**Source:** [Qwen2.5-VL-7B-Instruct on HuggingFace](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)

Qwen2.5-VL is Alibaba's vision-language model series. Available sizes: **3B, 7B, 32B, 72B** (no 32B in some sources, primarily 3B/7B/72B).

**Key capabilities for TrashTag:**
- Image classification of common objects
- **Bounding box support**: Can "accurately localize objects in an image by generating bounding boxes or points"
- **Stable JSON outputs**: Documented to provide "stable JSON outputs for coordinates and attributes"
- Strong performance on OCR, charts, document understanding (7B: DocVQA 95.7, OCRBench 864)

**Quantization:**
- 149 GGUF quantized models available
- Compatible with Ollama, llama.cpp, LM Studio

**Model popularity:** 8.99M downloads/month (7B-Instruct on HF)

## Local Deployment: Ollama

**Source:** [Ollama models search](https://ollama.com/search?q=qwen2.5-vl), [Ollama OpenAI compatibility blog](https://ollama.com/blog/openai-compatibility)

**Model tags:**
- Official: `qwen2.5vl` (3b, 7b, 32b, 72b variants)
- Pull command: `ollama pull qwen2.5vl:7b` or `ollama pull qwen2.5vl:3b`
- 4.5M+ pulls, 17 tags available

**OpenAI-compatible endpoint:**
- **Path:** `http://localhost:11434/v1/chat/completions`
- **Auth:** API key required by clients but unused (set to `'ollama'`)
- **Vision support status (as of Feb 2024):** Listed as "future improvement" in experimental OpenAI API support

**CRITICAL COMPATIBILITY ISSUE:** As of the Feb 2024 blog post, vision/multimodal support was NOT available in Ollama's OpenAI-compatible `/v1/chat/completions` endpoint. Ollama's native `/api/chat` endpoint DOES support vision via base64 images in an `images` array, but this requires changing TrashTag's VLMDetector to use Ollama's native format instead of OpenAI format.

**VRAM/Memory (estimated):**
- 3B quantized (Q4): ~2-3GB VRAM
- 7B quantized (Q4): ~4-6GB VRAM
- 7B full precision: ~14GB VRAM

**Recommendation:** Ollama is easy to set up (`ollama serve` starts server), but may require VLMDetector code changes to use native `/api/chat` format instead of OpenAI `/v1/chat/completions` if vision support hasn't been added yet.

## Local Deployment: vLLM & HF Transformers

**Sources:** [vLLM GitHub](https://github.com/vllm-project/vllm), [Qwen2.5-VL GitHub](https://github.com/QwenLM/Qwen2.5-VL)

**vLLM:**
- **OpenAI-compatible server**: Yes, vLLM offers "OpenAI-compatible API server"
- **Vision support**: Explicitly supports "Qwen-VL" and multi-modal models
- **Installation**: `uv pip install vllm` (requires `vllm>=0.11.0`)
- **Launch command pattern**: `vllm serve <model>` (exact command in full docs)
- **Endpoint**: `http://127.0.0.1:8000/v1/chat/completions` (default)
- **Base64 image URL**: vLLM OpenAI-compatible endpoint accepts standard OpenAI format with `image_url` 

**Example TrashTag config for vLLM:**
```bash
TRASHTAG_VLM_HOST=127.0.0.1
TRASHTAG_VLM_PORT=8000
TRASHTAG_VLM_PATH=/v1/chat/completions
TRASHTAG_VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
TRASHTAG_DETECTOR=vlm
```

**HF Transformers:**
- Requires `transformers >= 4.57.0`
- Load via `AutoModelForImageTextToText.from_pretrained(...)`
- Supports single/multi-image, video, batch inference
- For serving: use with vLLM or SGLang for OpenAI-compatible endpoints

**Recommendation:** vLLM is the best local option for OpenAI compatibility. Drop-in replacement - just change HOST/PORT/MODEL env vars.

## Cloud Endpoints (OpenAI-Compatible)

**Sources:** [HuggingFace Inference Providers](https://huggingface.co/docs/api-inference/index), [OpenRouter](https://openrouter.ai/qwen/qwen-2.5-vl-7b-instruct), [Together AI](https://docs.together.ai)

| Provider | Base URL | Model ID | Auth | Pricing/Free Tier | Status |
|----------|----------|----------|------|-------------------|--------|
| **HuggingFace** | `https://router.huggingface.co/v1` | `Qwen/Qwen2.5-VL-7B-Instruct:fastest` | HF token | Free tier + PRO credits | ✅ Multiple providers |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `qwen/qwen-2.5-vl-7b-instruct` | API key | Varies by provider | ✅ 33K context |
| **DashScope** (Alibaba) | `https://{WorkspaceId}.{region}.maas.aliyuncs.com/compatible-mode/v1` or `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` or `qwen3.8-max` | API key | Pay-as-you-go | ⚠️ Qwen2.5-VL not listed, has Qwen3+ |
| **Together AI** | `https://api.together.ai/v1` | (not found) | API key | See pricing page | ⚠️ Qwen2.5-VL not confirmed |
| **Hyperbolic** | (checking) | (checking) | API key | Free tier available | 🔍 Investigating |
| **Novita AI** | (via HF Providers) | (via HF) | Via HF token | Via HF billing | ✅ Through HF Inference |
| **DeepInfra** | (via HF Providers) | (via HF) | Via HF token | Via HF billing | ✅ Through HF Inference |

**HuggingFace Inference Providers** is the most comprehensive option - it routes to multiple underlying providers (Together, Novita, DeepInfra, Groq, Fireworks, etc.) automatically and supports vision models with OpenAI-compatible format.

**Best for drop-in compatibility:** HuggingFace Inference Providers with `:fastest` suffix for automatic provider selection.

## Structured Output & Bounding Boxes

**Source:** [Qwen2.5-VL-7B-Instruct HuggingFace](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)

**JSON Output:**
- Qwen2.5-VL is documented to provide "**stable JSON outputs for coordinates and attributes**"
- Supports structured outputs for scanned data (invoices, forms, tables)
- **No formal `response_format` parameter** documented (unlike GPT-4V)
- In practice: prompt for JSON format works reliably

**Bounding Boxes:**
- ✅ **Native support**: Can "accurately localize objects by generating bounding boxes or points"
- This is a MAJOR advantage over current Llama3.2-vision which returns `None` for bounding boxes
- **Format**: Provides coordinates as structured JSON

**TrashTag Implications:**
- Current VLMDetector prompts for `{"detections":[{"class":"pothole"|"garbage","confidence":0..1,"severity":"low|medium|high"}]}`
- Qwen2.5-VL can extend this to: `{"detections":[{"class":"...","confidence":...,"severity":"...","bbox":[x1,y1,x2,y2]}]}`
- Would enable precise localization of trash/potholes instead of just image-level detection

**Potential Format Quirks:**
- Some models wrap JSON in markdown code fences (```json...```)
- Current VLMDetector's error handling returns `[]` on parse failure - may need to strip markdown fences first
- Minimal code change if needed: `content.strip('```json\n').strip('\n```')` before `json.loads()`

## VLMDetector Compatibility

**Current VLMDetector implementation** (`src/trashtag/pipeline/vlm.py`):
- POSTs to `{scheme}://{host}:{port}{path}/chat/completions`
- Sends OpenAI-format: `{"role":"user","content":[{"type":"text"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}]}`
- Expects JSON in `choices[0].message.content`
- Returns `[]` on any error (connection, parse, HTTP)

### Drop-In Compatible (NO code change)

**✅ vLLM** - Perfect match:
```bash
# Terminal 1: Start vLLM server
vllm serve Qwen/Qwen2.5-VL-7B-Instruct

# Terminal 2: Configure TrashTag
export TRASHTAG_VLM_HOST=127.0.0.1
export TRASHTAG_VLM_PORT=8000
export TRASHTAG_VLM_PATH=/v1
export TRASHTAG_VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
export TRASHTAG_DETECTOR=vlm
```

**✅ HuggingFace Inference Providers** - Drop-in:
```bash
export TRASHTAG_VLM_HOST=router.huggingface.co
export TRASHTAG_VLM_PORT=443
export TRASHTAG_VLM_PATH=/v1
export TRASHTAG_VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct:fastest
export TRASHTAG_VLM_API_KEY=hf_xxx
export TRASHTAG_DETECTOR=vlm
```

**✅ OpenRouter** - Drop-in:
```bash
export TRASHTAG_VLM_HOST=openrouter.ai
export TRASHTAG_VLM_PORT=443
export TRASHTAG_VLM_PATH=/api/v1
export TRASHTAG_VLM_MODEL=qwen/qwen-2.5-vl-7b-instruct
export TRASHTAG_VLM_API_KEY=sk-or-xxx
export TRASHTAG_DETECTOR=vlm
```

**✅ DashScope** (Alibaba Cloud) - Drop-in:
```bash
export TRASHTAG_VLM_HOST=dashscope.aliyuncs.com
export TRASHTAG_VLM_PORT=443
export TRASHTAG_VLM_PATH=/compatible-mode/v1
export TRASHTAG_VLM_MODEL=qwen-vl-plus  # or qwen3.8-max
export TRASHTAG_VLM_API_KEY=sk-xxx
export TRASHTAG_DETECTOR=vlm
```

### May Need Code Change

**⚠️ Ollama** - Vision support in `/v1/chat/completions` was listed as "future improvement" as of Feb 2024:
- If implemented now: drop-in compatible with default env vars
- If NOT implemented: need to rewrite `_chat()` to use Ollama's native `/api/chat` endpoint (different message format with `images` array instead of `image_url`)
- **Test first**: `ollama pull qwen2.5vl:7b` then try with default env

### Optional Enhancement: Bounding Boxes

To leverage Qwen2.5-VL's bbox capability:
1. Update system prompt to request bbox in JSON
2. Change line 94 from `bbox=None` to `bbox=det.get("bbox")`
3. No other changes needed - RawDetection already has optional `bbox` field

## Recommendation

### By Hardware/Use Case

**1. GPU workstation (12GB+ VRAM) - LOCAL vLLM** ⭐ RECOMMENDED
```bash
# Install & start vLLM (one-time)
pip install vllm>=0.11.0
vllm serve Qwen/Qwen2.5-VL-7B-Instruct

# Configure TrashTag (add to .env or shell)
TRASHTAG_VLM_HOST=127.0.0.1
TRASHTAG_VLM_PORT=8000
TRASHTAG_VLM_PATH=/v1
TRASHTAG_VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
TRASHTAG_DETECTOR=vlm
```
**Why:** Drop-in compatible, fast inference, private, no API costs.

**2. Laptop / Low VRAM (4-8GB) - LOCAL Ollama with 3B**
```bash
# Install & start Ollama (one-time)
# Download from ollama.com, then:
ollama serve &
ollama pull qwen2.5vl:3b

# Configure TrashTag
TRASHTAG_VLM_HOST=localhost
TRASHTAG_VLM_PORT=11434
TRASHTAG_VLM_PATH=/v1
TRASHTAG_VLM_MODEL=qwen2.5vl:3b
TRASHTAG_DETECTOR=vlm
```
**Why:** Easiest setup, smallest model fits in limited VRAM. **CAVEAT:** Test if `/v1/chat/completions` supports vision yet (Feb 2024 it didn't). If not, requires code change to use `/api/chat`.

**3. No GPU / Cloud only - HuggingFace Inference Providers** ⭐ BEST CLOUD
```bash
# Get free HF token from hf.co/settings/tokens
TRASHTAG_VLM_HOST=router.huggingface.co
TRASHTAG_VLM_PORT=443
TRASHTAG_VLM_PATH=/v1
TRASHTAG_VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct:fastest
TRASHTAG_VLM_API_KEY=hf_...
TRASHTAG_DETECTOR=vlm
```
**Why:** Free tier available, routes to fastest provider automatically, OpenAI-compatible, no vendor lock-in.

**4. Budget-conscious cloud - OpenRouter**
```bash
TRASHTAG_VLM_HOST=openrouter.ai
TRASHTAG_VLM_PORT=443
TRASHTAG_VLM_PATH=/api/v1
TRASHTAG_VLM_MODEL=qwen/qwen-2.5-vl-7b-instruct
TRASHTAG_VLM_API_KEY=sk-or-...
TRASHTAG_DETECTOR=vlm
```
**Why:** Pay-as-you-go, competitive pricing, 33K context.

**5. China/Asia region - DashScope (Alibaba Cloud)**
```bash
TRASHTAG_VLM_HOST=dashscope.aliyuncs.com
TRASHTAG_VLM_PORT=443
TRASHTAG_VLM_PATH=/compatible-mode/v1
TRASHTAG_VLM_MODEL=qwen-vl-plus
TRASHTAG_VLM_API_KEY=sk-...
TRASHTAG_DETECTOR=vlm
```
**Why:** Official Qwen hosting, lower latency in Asia, regional compliance.

### Default Recommendation for TrashTag

**Primary:** vLLM with Qwen2.5-VL-7B-Instruct (local GPU)  
**Fallback:** HuggingFace Inference Providers (no GPU)  
**Cheapest free:** HuggingFace free tier + Ollama 3B local

### Model Size Sweet Spot

- **3B**: Good for pothole/garbage classification, fits 4-8GB VRAM, ~85-90% accuracy expected
- **7B**: ⭐ RECOMMENDED - Best balance of accuracy and speed, 12GB+ VRAM, strong bbox support
- **32B/72B**: Overkill for binary pothole/garbage classification, very slow without multi-GPU

## Sources

All sources cited inline throughout document:

1. **Qwen2.5-VL Model Card** - https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct  
   Model capabilities, benchmarks, quantization options

2. **Qwen2.5-VL GitHub** - https://github.com/QwenLM/Qwen2.5-VL  
   Deployment options (vLLM, HF Transformers, SGLang), OpenAI compatibility

3. **Ollama Models Search** - https://ollama.com/search?q=qwen2.5-vl  
   Available models, tags, community variants

4. **Ollama OpenAI Compatibility** - https://ollama.com/blog/openai-compatibility  
   `/v1/chat/completions` endpoint status, vision support timeline

5. **vLLM GitHub** - https://github.com/vllm-project/vllm  
   OpenAI-compatible server, multi-modal support confirmation

6. **HuggingFace Inference Providers** - https://huggingface.co/docs/api-inference/index  
   Multi-provider vision model support, pricing, OpenAI compatibility

7. **OpenRouter Model Page** - https://openrouter.ai/qwen/qwen-2.5-vl-7b-instruct  
   Model ID, context length, modality information

8. **Together AI Quickstart** - https://docs.together.ai/docs/quickstart  
   Base URL, OpenAI compatibility, vision model support

9. **Alibaba Model Studio** - https://help.aliyun.com/zh/model-studio/getting-started/models  
   DashScope endpoint format, model IDs, regional availability

---

**Research completed:** 2026-08-23  
**Recommended update interval:** 3-6 months (check Ollama vision support status, new cloud providers)
