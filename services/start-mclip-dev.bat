@echo off
echo Starting M-CLIP Embedding Service (Development Mode)...
cd /d "%~dp0"

echo Setting up development environment...
set PYTHONPATH=%PYTHONPATH%;.
set LOG_LEVEL=DEBUG

echo Installing Python dependencies...
pip install -r requirements-mclip.txt

echo Starting M-CLIP service with auto-reload on port 8002...
echo Service will be available at: http://localhost:8002
echo API documentation: http://localhost:8002/docs
echo Health check: http://localhost:8002/health
echo.
echo Press Ctrl+C to stop the service
echo.

uvicorn mclip-service:app --host 0.0.0.0 --port 8002 --reload --log-level debug

pause