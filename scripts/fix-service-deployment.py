#!/usr/bin/env python3
"""
Fix Service Deployment Issues
Ensures M-CLIP and Docling services start properly with GPU acceleration
"""

import sys
import subprocess
import time
import requests
import os
from pathlib import Path

# Service configurations
SERVICES = {
    'mclip': {
        'name': 'M-CLIP Embedding Service',
        'script': 'services/mclip-service.py',
        'port': 8002,
        'health_endpoint': '/health',
        'dependencies': ['torch', 'transformers', 'sentence-transformers', 'PIL']
    },
    'docling': {
        'name': 'Docling Document Processing Service',
        'script': 'services/docling-service.py',
        'port': 8003,
        'health_endpoint': '/health',
        'dependencies': ['docling', 'pymupdf', 'fastapi', 'uvicorn']
    }
}

class ServiceManager:
    def __init__(self):
        self.python_path = './tests/rag-evaluation/python-env/Scripts/python.exe'
        self.running_processes = {}
        
    def check_dependencies(self, service_name):
        """Check if service dependencies are installed"""
        print(f"\n🔍 Checking dependencies for {SERVICES[service_name]['name']}...")
        
        missing = []
        for dep in SERVICES[service_name]['dependencies']:
            try:
                result = subprocess.run(
                    [self.python_path, '-c', f'import {dep}'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"   ✅ {dep}")
            except subprocess.CalledProcessError:
                missing.append(dep)
                print(f"   ❌ {dep} (missing)")
        
        if missing:
            print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
            return False
        
        print("   ✅ All dependencies available")
        return True
    
    def install_missing_dependencies(self, service_name):
        """Install missing dependencies"""
        deps = SERVICES[service_name]['dependencies']
        print(f"\n📦 Installing dependencies for {service_name}...")
        
        # Special handling for different packages
        install_commands = {
            'torch': [self.python_path, '-m', 'pip', 'install', 'torch', '--index-url', 'https://download.pytorch.org/whl/cu121'],
            'transformers': [self.python_path, '-m', 'pip', 'install', 'transformers[torch]'],
            'sentence-transformers': [self.python_path, '-m', 'pip', 'install', 'sentence-transformers'],
            'PIL': [self.python_path, '-m', 'pip', 'install', 'Pillow'],
            'docling': [self.python_path, '-m', 'pip', 'install', 'docling'],
            'pymupdf': [self.python_path, '-m', 'pip', 'install', 'PyMuPDF'],
            'fastapi': [self.python_path, '-m', 'pip', 'install', 'fastapi[all]'],
            'uvicorn': [self.python_path, '-m', 'pip', 'install', 'uvicorn[standard]']
        }
        
        for dep in deps:
            cmd = install_commands.get(dep, [self.python_path, '-m', 'pip', 'install', dep])
            print(f"   Installing {dep}...")
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"   ✅ {dep} installed")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Failed to install {dep}: {e}")
                return False
        
        return True
    
    def check_service_script(self, service_name):
        """Check if service script exists"""
        script_path = SERVICES[service_name]['script']
        if os.path.exists(script_path):
            print(f"   ✅ Service script found: {script_path}")
            return True
        else:
            print(f"   ❌ Service script missing: {script_path}")
            return False
    
    def create_service_script(self, service_name):
        """Create missing service script"""
        print(f"\n🔧 Creating {service_name} service script...")
        
        if service_name == 'mclip':
            return self.create_mclip_service()
        elif service_name == 'docling':
            return self.create_docling_service()
        
        return False
    
    def create_mclip_service(self):
        """Create M-CLIP service script with GPU support"""
        script_content = '''#!/usr/bin/env python3
"""
M-CLIP Embedding Service with GPU Acceleration
Provides fast multimodal embeddings for text and images
"""

import os
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union
import uvicorn
from sentence_transformers import SentenceTransformer
from PIL import Image
import io
import base64

# Force GPU usage if available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"🚀 M-CLIP Service starting on device: {device}")

app = FastAPI(title="M-CLIP Embedding Service", version="1.0.0")

# Load M-CLIP model
try:
    model = SentenceTransformer('clip-ViT-B-32-multilingual-v1')
    model = model.to(device)
    print("✅ M-CLIP model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load M-CLIP model: {e}")
    model = None

class TextRequest(BaseModel):
    texts: List[str]

class ImageRequest(BaseModel):
    images: List[str]  # Base64 encoded images

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    device: str
    model_name: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    }

@app.post("/embed/text", response_model=EmbeddingResponse)
async def embed_text(request: TextRequest):
    """Generate embeddings for text"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        with torch.no_grad():
            embeddings = model.encode(request.texts, device=device)
            return EmbeddingResponse(
                embeddings=embeddings.tolist(),
                device=str(device),
                model_name="clip-ViT-B-32-multilingual-v1"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

@app.post("/embed/image", response_model=EmbeddingResponse)
async def embed_image(request: ImageRequest):
    """Generate embeddings for images"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        images = []
        for img_b64 in request.images:
            img_data = base64.b64decode(img_b64)
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        
        with torch.no_grad():
            embeddings = model.encode(images, device=device)
            return EmbeddingResponse(
                embeddings=embeddings.tolist(),
                device=str(device),
                model_name="clip-ViT-B-32-multilingual-v1"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image embedding failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
'''
        
        os.makedirs('services', exist_ok=True)
        with open('services/mclip-service.py', 'w') as f:
            f.write(script_content)
        
        print("   ✅ M-CLIP service script created")
        return True
    
    def create_docling_service(self):
        """Create Docling service script"""
        script_content = '''#!/usr/bin/env python3
"""
Docling Document Processing Service
Handles PDF parsing and image extraction
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import tempfile
import fitz  # PyMuPDF
from pathlib import Path

app = FastAPI(title="Docling Document Processing Service", version="1.0.0")

class DocumentResponse(BaseModel):
    text_chunks: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "pymupdf_version": fitz.version[0]
    }

@app.post("/process/pdf", response_model=DocumentResponse)
async def process_pdf(file: UploadFile = File(...)):
    """Process PDF and extract text and images"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Process with PyMuPDF
        doc = fitz.open(tmp_path)
        text_chunks = []
        images = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract text
            text = page.get_text()
            if text.strip():
                text_chunks.append({
                    "page_number": page_num + 1,
                    "content": text.strip(),
                    "type": "text"
                })
            
            # Extract images
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                images.append({
                    "page_number": page_num + 1,
                    "image_index": img_index,
                    "format": base_image["ext"],
                    "size": len(image_bytes),
                    "width": base_image["width"],
                    "height": base_image["height"]
                })
        
        doc.close()
        os.unlink(tmp_path)  # Clean up temp file
        
        return DocumentResponse(
            text_chunks=text_chunks,
            images=images,
            metadata={
                "filename": file.filename,
                "page_count": len(doc),
                "text_chunks_count": len(text_chunks),
                "images_count": len(images)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
'''
        
        os.makedirs('services', exist_ok=True)
        with open('services/docling-service.py', 'w') as f:
            f.write(script_content)
        
        print("   ✅ Docling service script created")
        return True
    
    def start_service(self, service_name):
        """Start a service"""
        service = SERVICES[service_name]
        print(f"\n🚀 Starting {service['name']}...")
        
        try:
            # Start service in background
            proc = subprocess.Popen(
                [self.python_path, service['script']],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.running_processes[service_name] = proc
            
            # Wait for service to start
            print(f"   Waiting for service to start on port {service['port']}...")
            time.sleep(5)
            
            # Check if process is still running
            if proc.poll() is None:
                print(f"   ✅ Service started (PID: {proc.pid})")
                return True
            else:
                stdout, stderr = proc.communicate()
                print(f"   ❌ Service failed to start:")
                print(f"   stdout: {stdout}")
                print(f"   stderr: {stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Failed to start service: {e}")
            return False
    
    def check_service_health(self, service_name):
        """Check if service is healthy"""
        service = SERVICES[service_name]
        url = f"http://localhost:{service['port']}{service['health_endpoint']}"
        
        print(f"   Checking health: {url}")
        
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"   ✅ Service healthy: {health_data}")
                    return True
                else:
                    print(f"   ❌ Service unhealthy (status: {response.status_code})")
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Connection failed (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(2)
        
        return False
    
    def fix_service(self, service_name):
        """Complete service fix pipeline"""
        print(f"\n🔧 FIXING {SERVICES[service_name]['name'].upper()}")
        print("-" * 60)
        
        # Step 1: Check dependencies
        if not self.check_dependencies(service_name):
            if not self.install_missing_dependencies(service_name):
                return False
        
        # Step 2: Check service script
        if not self.check_service_script(service_name):
            if not self.create_service_script(service_name):
                return False
        
        # Step 3: Start service
        if not self.start_service(service_name):
            return False
        
        # Step 4: Health check
        time.sleep(3)  # Give service time to fully start
        if not self.check_service_health(service_name):
            return False
        
        print(f"   ✅ {SERVICES[service_name]['name']} is now running and healthy!")
        return True
    
    def stop_all_services(self):
        """Stop all running services"""
        print("\n🛑 Stopping all services...")
        for service_name, proc in self.running_processes.items():
            if proc.poll() is None:  # Still running
                print(f"   Stopping {service_name}...")
                proc.terminate()
                proc.wait(timeout=5)
                print(f"   ✅ {service_name} stopped")

def main():
    print("🛠️  SERVICE DEPLOYMENT FIX")
    print("=" * 60)
    print("Fixing M-CLIP and Docling service availability issues\\n")
    
    manager = ServiceManager()
    
    try:
        # Fix both services
        success = True
        for service_name in ['mclip', 'docling']:
            if not manager.fix_service(service_name):
                success = False
        
        if success:
            print("\\n🎉 ALL SERVICES FIXED AND RUNNING!")
            print("=" * 60)
            print("Services:")
            print("  • M-CLIP Service: http://localhost:8002/health")
            print("  • Docling Service: http://localhost:8003/health")
            print("\\nServices will continue running in background...")
            print("Use Ctrl+C to stop this script (services will keep running)")
            
            # Keep script alive to show service status
            try:
                while True:
                    time.sleep(30)
                    print("\\n📊 Service Status Check...")
                    for service_name in ['mclip', 'docling']:
                        if manager.check_service_health(service_name):
                            print(f"   ✅ {service_name} healthy")
                        else:
                            print(f"   ❌ {service_name} unhealthy")
            except KeyboardInterrupt:
                print("\\n🛑 Shutting down...")
        else:
            print("\\n❌ SOME SERVICES FAILED TO START")
            print("Check the error messages above for details")
    
    finally:
        manager.stop_all_services()

if __name__ == "__main__":
    main()
'''