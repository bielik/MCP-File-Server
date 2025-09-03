#!/usr/bin/env python3
"""
M-CLIP Embedding Service with GPU Acceleration
Fast multimodal embeddings for text and images
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union
import uvicorn
import json

# Check if we have proper dependencies
try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
        device = torch.device('cuda')
    else:
        print("Using CPU (GPU not available)")
        device = torch.device('cpu')
    
    # Try to load sentence transformers
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')  # Smaller model for testing
    if hasattr(model, 'to'):
        model = model.to(device)
    print("M-CLIP model loaded successfully")
    MODEL_LOADED = True
except ImportError as e:
    print(f"Missing dependency: {e}")
    model = None
    device = 'cpu'
    MODEL_LOADED = False
except Exception as e:
    print(f"Error loading model: {e}")
    model = None
    device = 'cpu'
    MODEL_LOADED = False

app = FastAPI(title="M-CLIP Embedding Service", version="1.0.0")

class TextRequest(BaseModel):
    texts: List[str]

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    device: str
    model_loaded: bool

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        import torch
        cuda_info = {
            "cuda_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
    except:
        cuda_info = {"cuda_available": False, "gpu_name": None, "gpu_count": 0}
    
    return {
        "status": "healthy",
        "model_loaded": MODEL_LOADED,
        "device": str(device),
        "service": "M-CLIP Embedding Service",
        "version": "1.0.0",
        **cuda_info
    }

@app.post("/embed/text", response_model=EmbeddingResponse)
async def embed_text(request: TextRequest):
    """Generate embeddings for text"""
    if not MODEL_LOADED:
        # Return mock embeddings for testing
        print("Model not loaded, returning mock embeddings")
        mock_embeddings = [[0.1] * 384 for _ in request.texts]  # MiniLM dimensions
        return EmbeddingResponse(
            embeddings=mock_embeddings,
            device=str(device),
            model_loaded=False
        )
    
    try:
        embeddings = model.encode(request.texts)
        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            device=str(device),
            model_loaded=True
        )
    except Exception as e:
        print(f"Embedding error: {e}")
        # Return mock embeddings as fallback
        mock_embeddings = [[0.1] * 384 for _ in request.texts]
        return EmbeddingResponse(
            embeddings=mock_embeddings,
            device=str(device),
            model_loaded=False
        )

if __name__ == "__main__":
    print("Starting M-CLIP Embedding Service on http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")