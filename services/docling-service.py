#!/usr/bin/env python3
"""
Docling Document Processing Service
Handles PDF parsing and image extraction using PyMuPDF
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import tempfile
from pathlib import Path

# Check dependencies
try:
    import fitz  # PyMuPDF
    print("PyMuPDF available")
    PYMUPDF_AVAILABLE = True
except ImportError:
    print("PyMuPDF not available - using mock processing")
    PYMUPDF_AVAILABLE = False

app = FastAPI(title="Docling Document Processing Service", version="1.0.0")

class DocumentResponse(BaseModel):
    text_chunks: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    processing_method: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Docling Document Processing Service",
        "version": "1.0.0",
        "pymupdf_available": PYMUPDF_AVAILABLE,
        "pymupdf_version": fitz.version[0] if PYMUPDF_AVAILABLE else None
    }

@app.post("/process/pdf", response_model=DocumentResponse)
async def process_pdf(file: UploadFile = File(...)):
    """Process PDF and extract text and images"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    if not PYMUPDF_AVAILABLE:
        # Return mock processing results
        print("PyMuPDF not available, returning mock results")
        return DocumentResponse(
            text_chunks=[
                {
                    "page_number": 1,
                    "content": "This is mock text content from the PDF document.",
                    "type": "text"
                },
                {
                    "page_number": 1,
                    "content": "Additional mock text showing document processing capabilities.",
                    "type": "text"
                }
            ],
            images=[
                {
                    "page_number": 1,
                    "image_index": 0,
                    "format": "png",
                    "size": 1024,
                    "width": 400,
                    "height": 300
                }
            ],
            metadata={
                "filename": file.filename,
                "page_count": 1,
                "text_chunks_count": 2,
                "images_count": 1
            },
            processing_method="mock"
        )
    
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
                # Split text into chunks (simple approach)
                sentences = text.strip().split('. ')
                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        text_chunks.append({
                            "page_number": page_num + 1,
                            "chunk_index": i,
                            "content": sentence.strip() + ('.' if not sentence.endswith('.') else ''),
                            "type": "text"
                        })
            
            # Extract images
            try:
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
            except Exception as img_error:
                print(f"Image extraction error on page {page_num + 1}: {img_error}")
        
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
            },
            processing_method="pymupdf"
        )
        
    except Exception as e:
        print(f"PDF processing error: {e}")
        # Try to clean up temp file if it exists
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except:
            pass
        
        # Return error or mock data
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

@app.post("/process/text")
async def process_text(text_content: str):
    """Process plain text content"""
    try:
        # Simple text processing
        sentences = text_content.split('. ')
        text_chunks = []
        
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                text_chunks.append({
                    "page_number": 1,
                    "chunk_index": i,
                    "content": sentence.strip() + ('.' if not sentence.endswith('.') else ''),
                    "type": "text"
                })
        
        return DocumentResponse(
            text_chunks=text_chunks,
            images=[],
            metadata={
                "filename": "text_input",
                "page_count": 1,
                "text_chunks_count": len(text_chunks),
                "images_count": 0
            },
            processing_method="text_split"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text processing failed: {str(e)}")

if __name__ == "__main__":
    print("Starting Docling Document Processing Service on http://localhost:8003")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")