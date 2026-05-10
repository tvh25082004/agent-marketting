# Tinasoft Agentic Marketing System

AI Agentic Marketing System for automated music video production using LangGraph, FastAPI, and Next.js.

## Architecture

### Backend (FastAPI + LangGraph)
Provides an orchestration layer for AI agents using a directed graph workflow. Includes specialized agents for:
- **Crawler**: Scraping music assets
- **Voice / Lyric**: Processing audio and generating AI voices and subtitles
- **Video / Lipsync / Karaoke**: Rendering videos and compositing effects
- **Supervisor**: Orchestrating the workflow and evaluating results

### Frontend (Next.js + Tailwind)
A modern, dynamic user interface for managing agents, tracking tasks, and viewing generated videos.

## Quick Start

### Backend
```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Features
- **Multi-model LLM integration** (OpenAI, Anthropic, Gemini, Ollama via 9Router)
- **Langfuse Monitoring** for comprehensive LLM observability
- **Agentic Workflow** built on LangGraph for stateful multi-agent execution
