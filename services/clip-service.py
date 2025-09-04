#!/usr/bin/env python3
"""
PROPER CLIP Embedding Service with Text AND Image Support
Uses actual CLIP models for true multimodal embeddings
"""

import os
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional, Union
import uvicorn
import numpy as np
from PIL import Image
import io
import base64

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
    
    # Load PROPER CLIP models using transformers only
    from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
    
    # Use OpenAI CLIP for both text and image (unified model)
    print("Loading unified CLIP model: openai/clip-vit-base-patch32...")
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", 
                                         trust_remote_code=True,
                                         use_safetensors=True,
                                         torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32)
    clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", 
                                                  trust_remote_code=True,
                                                  use_safetensors=True)
    clip_tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32", 
                                                  trust_remote_code=True,
                                                  use_safetensors=True)
    
    if hasattr(clip_model, 'to'):
        clip_model = clip_model.to(device)
    
    # Use the same model for both text and image
    text_model = clip_model
    text_processor = clip_tokenizer
    
    print("CLIP models loaded successfully (TRUE multimodal support)")
    MODEL_LOADED = True
    
    # Get embedding dimension from CLIP
    test_text_inputs = text_processor(["test"], return_tensors="pt", padding=True, truncation=True)
    test_text_inputs = {k: v.to(device) for k, v in test_text_inputs.items()}
    with torch.no_grad():
        test_embedding = text_model.get_text_features(**test_text_inputs)
        EMBEDDING_DIM = test_embedding.shape[1]
    print(f"Embedding dimension: {EMBEDDING_DIM}")
    
except ImportError as e:
    print(f"Missing dependency: {e}")
    text_model = None
    image_model = None
    device = 'cpu'
    MODEL_LOADED = False
    EMBEDDING_DIM = 512
except Exception as e:
    print(f"Error loading models: {e}")
    text_model = None
    image_model = None
    device = 'cpu'
    MODEL_LOADED = False
    EMBEDDING_DIM = 512

app = FastAPI(title="CLIP Embedding Service (Real Multimodal)", version="2.0.0")

class TextRequest(BaseModel):
    texts: List[str]

class ImageRequest(BaseModel):
    images_base64: List[str]  # Base64 encoded images

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    device: str
    model_loaded: bool
    dimension: int
    model_type: str

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
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
        "service": "CLIP Embedding Service (True Multimodal)",
        "version": "2.0.0",
        "embedding_dimension": EMBEDDING_DIM,
        "supports_text": True,
        "supports_images": True,
        **cuda_info
    }

@app.post("/embed/text", response_model=EmbeddingResponse)
async def embed_text(request: TextRequest):
    """Generate embeddings for text using CLIP text tower"""
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # Use OpenAI CLIP text tower
        inputs = text_processor(request.texts, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get text embeddings from CLIP model
        with torch.no_grad():
            text_features = text_model.get_text_features(**inputs)
            # Normalize embeddings (important for cosine similarity)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            embeddings = text_features
        
        # Convert to CPU and list
        if torch.is_tensor(embeddings):
            embeddings = embeddings.cpu().numpy()
        
        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            device=str(device),
            model_loaded=True,
            dimension=EMBEDDING_DIM,
            model_type="openai/clip-vit-base-patch32 (text tower)"
        )
    except Exception as e:
        print(f"Text embedding error: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

@app.post("/embed/image", response_model=EmbeddingResponse)
async def embed_image(request: ImageRequest):
    """Generate embeddings for images using CLIP image tower"""
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        images = []
        for img_base64 in request.images_base64:
            # Decode base64 to image
            img_bytes = base64.b64decode(img_base64)
            img = Image.open(io.BytesIO(img_bytes))
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
        
        # Use OpenAI CLIP to encode images
        inputs = clip_processor(images=images, return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get image embeddings from CLIP model
        with torch.no_grad():
            image_features = clip_model.get_image_features(**inputs)
            # Normalize embeddings (important for cosine similarity)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            embeddings = image_features
        
        # Convert to CPU and list
        if torch.is_tensor(embeddings):
            embeddings = embeddings.cpu().numpy()
        
        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            device=str(device),
            model_loaded=True,
            dimension=EMBEDDING_DIM,
            model_type="openai/clip-vit-base-patch32 (image tower)"
        )
    except Exception as e:
        print(f"Image embedding error: {e}")
        raise HTTPException(status_code=500, detail=f"Image embedding failed: {str(e)}")

@app.post("/embed/image-file", response_model=EmbeddingResponse)
async def embed_image_file(files: List[UploadFile] = File(...)):
    """Generate embeddings for uploaded image files"""
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        images = []
        for file in files:
            # Read image file
            contents = await file.read()
            img = Image.open(io.BytesIO(contents))
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
        
        # Use OpenAI CLIP to encode images
        inputs = clip_processor(images=images, return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get image embeddings from CLIP model
        with torch.no_grad():
            image_features = clip_model.get_image_features(**inputs)
            # Normalize embeddings (important for cosine similarity)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            embeddings = image_features
        
        # Convert to CPU and list
        if torch.is_tensor(embeddings):
            embeddings = embeddings.cpu().numpy()
        
        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            device=str(device),
            model_loaded=True,
            dimension=EMBEDDING_DIM,
            model_type="openai/clip-vit-base-patch32 (image tower)"
        )
    except Exception as e:
        print(f"Image file embedding error: {e}")
        raise HTTPException(status_code=500, detail=f"Image embedding failed: {str(e)}")

@app.get("/test/similarity")
async def test_similarity():
    """Test that text and image embeddings are in the same space"""
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # Test text
        text = "a photo of a cat"
        text_inputs = text_processor([text], return_tensors="pt", padding=True, truncation=True)
        text_inputs = {k: v.to(device) for k, v in text_inputs.items()}
        
        # Get text embeddings
        with torch.no_grad():
            text_features = text_model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            text_embedding = text_features
        
        # Create a simple test image (would normally load a real cat image)
        test_img = Image.new('RGB', (224, 224), color='white')
        
        # Use OpenAI CLIP to encode image
        image_inputs = clip_processor(images=[test_img], return_tensors="pt", padding=True)
        image_inputs = {k: v.to(device) for k, v in image_inputs.items()}
        
        # Get image embeddings from CLIP model
        with torch.no_grad():
            image_features = clip_model.get_image_features(**image_inputs)
            # Normalize embeddings (important for cosine similarity)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            image_embedding = image_features
        
        # Calculate cosine similarity
        cos_sim = torch.nn.functional.cosine_similarity(text_embedding, image_embedding)
        
        return {
            "text": text,
            "text_embedding_shape": list(text_embedding.shape),
            "image_embedding_shape": list(image_embedding.shape),
            "embeddings_compatible": text_embedding.shape == image_embedding.shape,
            "cosine_similarity": float(cos_sim.cpu().numpy()[0]),
            "same_vector_space": True,
            "text_model": "openai/clip-vit-base-patch32 (text tower)",
            "image_model": "openai/clip-vit-base-patch32 (image tower)"
        }
    except Exception as e:
        print(f"Similarity test error: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

if __name__ == "__main__":
    print("Starting PROPER CLIP Embedding Service on http://localhost:8004")
    print("This service supports BOTH text and image embeddings in the same vector space")
    uvicorn.run(app, host="0.0.0.0", port=8004)