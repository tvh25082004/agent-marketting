# Tinasoft-Agentic-Marketing

AI Agentic Marketing System for automated music video production using LangGraph.

## Quick Start

```bash
# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Architecture

### Backend (FastAPI + LangGraph)
- `/backend/app/agents/` - Agent definitions (Supervisor, Crawler, Music, Lyric, Voice, Video, Lipsync, Karaoke, Render, Feedback)
- `/backend/app/workflow/` - LangGraph state graph and nodes
- `/backend/app/tools/` - Tool implementations (crawler, audio, video, lyric)
- `/backend/app/memory/` - Memory management (short-term + persistent)
- `/backend/app/models/` - Multi-model support (OpenAI, Anthropic, Ollama)
- `/backend/app/api/` - REST API endpoints
- `/backend/app/services/` - Langfuse integration, scheduler

### Frontend (Next.js + Tailwind)
- `/frontend/src/components/Chat/` - Chat interface
- `/frontend/src/components/AgentFlow/` - Workflow visualization
- `/frontend/src/components/Video/` - Video gallery
- `/frontend/src/components/Settings/` - Settings panel

## Commands

```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Docker
docker-compose up --build
```

## Workflow

1. **Supervisor** - Phân tích yêu cầu, lập kế hoạch workflow
2. **Crawler** - Crawl nhạc từ laomusic.net
3. **Music** - Xử lý audio, chuẩn hóa chất lượng
4. **Lyric** - Lấy lyrics, tạo SRT/ASS subtitles
5. **Voice** - Tạo giọng ca sĩ nữ AI (edge-tts)
6. **Video** - Tạo video studio với ánh sáng đẹp
7. **Lipsync** - Đồng bộ khớp miệng
8. **Karaoke** - Thêm lyric karaoke phía dưới
9. **Render** - Render video cuối cùng 30-60s
10. **Feedback** - Đánh giá chất lượng, học từ feedback

## Models Supported
- **9Router Gateway**: kết nối 60+ providers qua 1 endpoint local
  - `gemini` (combo - recommended)
  - `gc/gemini-3-flash-preview`, `gc/gemini-3-pro-preview`
  - `ag/gemini-3-flash`, `ag/gemini-3.1-pro-low`
  - `cu/claude-4.5-sonnet`, `cu/claude-4.5-haiku`
  - `cx/gpt-5.1-codex`, `cx/gpt-5.2`, `cx/gpt-5.3-codex`
- OpenAI: gpt-4o, gpt-4o-mini (fallback)
- Anthropic: claude-sonnet-4-20250514, claude-haiku-3-5 (fallback)
- Ollama: llama3, mistral, qwen2 (local)

## 9Router Setup
```bash
# 9Router đã được cài đặt và chạy
npm install -g 9router
9router  # Dashboard: http://localhost:20128/dashboard

# API Key: sk-259b9f08e24eebc4-5afkfh-ccf90543
# Endpoint: http://localhost:20128/v1

# Kết nối providers (OAuth hoặc API Key):
# Dashboard → Providers → Add Provider
# Khuyến nghị: Gemini CLI (free), GitHub Copilot (free edu), AntiGravity
```

## Monitoring
- Langfuse for LLM observability
- Real-time token/cost tracking
- Feedback scoring system
