import os
import json
from typing import List, Dict, Any
from app.services import permission_service

SHARED_FS_PATH = "/source"

def read_file(path: str) -> str:
    """Reads the content of a file."""
    permission_service.check_access(path, 'read')
    full_path = permission_service.get_safe_path(path)
    
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"'{path}' is not a valid file.")

    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()

def list_files(path: str) -> List[Dict[str, Any]]:
    """Lists files and directories at a given path."""
    permission_service.check_access(path, 'read')
    full_path = permission_service.get_safe_path(path)
    
    if not os.path.isdir(full_path):
        raise FileNotFoundError(f"'{path}' is not a valid directory.")

    items = []
    for item_name in os.listdir(full_path):
        item_path = os.path.join(full_path, item_name)
        is_dir = os.path.isdir(item_path)
        items.append({
            "name": item_name,
            "path": os.path.join(path, item_name),
            "type": "directory" if is_dir else "file"
        })
    return items

def write_file(path: str, content: str) -> str:
    """Writes content to a file, creating it if it doesn't exist."""
    permission_service.check_access(path, 'write')
    full_path = permission_service.get_safe_path(path)
    
    # Ensure parent directory exists
    parent_dir = os.path.dirname(full_path)
    os.makedirs(parent_dir, exist_ok=True)

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return f"Successfully wrote {len(content)} characters to '{path}'."
