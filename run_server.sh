#!/bin/bash
# Tinasoft AI Video Studio - Startup Script
# MacOS M3 Optimized

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "========================================"
echo "  Tinasoft AI Video Studio"
echo "  MacOS M3 Optimized"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check dependencies
echo -e "${BLUE}[1/5] Checking dependencies...${NC}"

command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Python3 required${NC}"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo -e "${RED}pip3 required${NC}"; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e "${RED}Node.js required${NC}"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo -e "${RED}ffmpeg required - install: brew install ffmpeg${NC}"; exit 1; }

echo -e "  ${GREEN}All dependencies found${NC}"

# Setup backend
echo -e "${BLUE}[2/5] Setting up backend...${NC}"
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo -e "  ${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate

if [ ! -f "venv/installed.flag" ]; then
    echo -e "  ${YELLOW}Installing Python dependencies...${NC}"
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    pip install numpy opencv-python-headless insightface onnxruntime -q
    touch venv/installed.flag
    echo -e "  ${GREEN}Dependencies installed${NC}"
fi

# Setup frontend
echo -e "${BLUE}[3/5] Setting up frontend...${NC}"
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo -e "  ${YELLOW}Installing Node.js dependencies...${NC}"
    npm install --silent 2>/dev/null
    echo -e "  ${GREEN}Dependencies installed${NC}"
fi

# Prepare directories
echo -e "${BLUE}[4/5] Preparing directories...${NC}"
mkdir -p "$PROJECT_DIR/input" "$PROJECT_DIR/output/videos" "$PROJECT_DIR/temp"

echo -e "  ${GREEN}Directories ready${NC}"

# Start services
echo -e "${BLUE}[5/5] Starting services...${NC}"

cd "$BACKEND_DIR"
source venv/bin/activate

echo -e "  ${GREEN}Starting backend on http://localhost:8000${NC}"
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!

cd "$FRONTEND_DIR"
echo -e "  ${GREEN}Starting frontend on http://localhost:3000${NC}"
npm run dev -- -p 3000 &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo -e "  ${GREEN}System Ready!${NC}"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop"
echo "========================================"

# Cleanup on exit
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
