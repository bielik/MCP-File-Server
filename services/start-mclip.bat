@echo off
echo Starting M-CLIP Embedding Service...
cd /d "%~dp0"

echo Checking Python dependencies...
pip install -r requirements-mclip.txt

echo Starting M-CLIP service on port 8002...
python mclip-service.py

pause