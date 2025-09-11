from fastapi import APIRouter

router = APIRouter()

@router.get("/config")
def get_config():
    """
    Returns the initial server configuration for the UI.
    """
    # This will be populated with actual config data from the DB or files.
    return {
        "server_port": 8000,
        "permissions": {
            "context": ["/shared-fs/docs"],
            "working": ["/shared-fs/projects"],
            "output": ["/shared-fs/output"]
        },
        "file_system_stats": {
            "total_files": 1024,
            "total_size_mb": 256
        }
    }
