@echo off
echo Starting Qdrant vector database...
cd /d "%~dp0..\docker"
docker-compose up -d qdrant
echo Waiting for Qdrant to be ready...
timeout /t 10 /nobreak > nul
echo Checking Qdrant health...
curl -f http://localhost:6333/health
if %errorlevel% equ 0 (
    echo Qdrant is healthy and ready!
) else (
    echo Qdrant health check failed. Please check logs: docker-compose logs qdrant
)
pause