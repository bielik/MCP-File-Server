@echo off
echo Setting up Qdrant multimodal collections...
cd /d "%~dp0"

echo Installing Python dependencies...
pip install -r requirements-qdrant.txt

echo Running collection setup...
python setup-qdrant-collections.py

echo Collection setup completed.
pause