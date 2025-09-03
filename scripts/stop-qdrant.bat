@echo off
echo Stopping Qdrant vector database...
cd /d "%~dp0..\docker"
docker-compose down
echo Qdrant has been stopped.
pause