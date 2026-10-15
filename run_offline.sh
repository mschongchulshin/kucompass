#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${MODEL:-qwen3:8b}"

unset GROQ_API_KEY CEREBRAS_API_KEY GEMINI_API_KEY GOOGLE_API_KEY \
      OPENROUTER_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY LLM_API_KEY 2>/dev/null || true

export OFFLINE_MODE=1
export LLM_MODEL="$MODEL"

if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama를 시작합니다..."
    ollama serve >/dev/null 2>&1 &
    until curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; do sleep 1; done
fi

if ! ollama list | awk 'NR>1{print $1}' | grep -qx "$MODEL"; then
    echo "모델 $MODEL 을 내려받습니다..."
    ollama pull "$MODEL"
fi

echo
echo "  모델      $MODEL"
echo "  주소      http://127.0.0.1:${PORT:-7860}"
echo "  외부전송  차단됨 (OFFLINE_MODE=1)"
echo
exec python3 gradio_app.py
