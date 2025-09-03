@echo off
echo Starting Docling PDF Processing Service...
cd /d "%~dp0"

echo Installing Python dependencies...
pip install -r requirements-docling.txt

echo Creating necessary directories...
mkdir temp\docling 2>nul
mkdir cache\docling 2>nul

echo Starting Docling service on port 8003...
echo Service will be available at: http://localhost:8003
echo API documentation: http://localhost:8003/docs
echo Health check: http://localhost:8003/health
echo.
echo Press Ctrl+C to stop the service
echo.

python docling-service.py

pause