#!/usr/bin/env bash
set -uo pipefail

if pgrep -f "cloudflared tunnel" >/dev/null; then
    pkill -f "cloudflared tunnel"
    echo "공개 터널 종료됨. 외부 URL은 즉시 접속 불가."
else
    echo "실행 중인 터널 없음."
fi

if [ "${1:-}" = "all" ]; then
    if pgrep -f "gradio_app.py" >/dev/null; then
        pkill -f "gradio_app.py"
        echo "웹 서버 종료됨."
    else
        echo "실행 중인 웹 서버 없음."
    fi
    echo "(Ollama는 유지. 내리려면 pkill ollama)"
fi
