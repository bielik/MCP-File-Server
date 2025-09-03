#!/usr/bin/env python3
"""
RAG Evaluation Service - Python Backend
Provides REST API for RAG evaluation metrics without requiring full RAGAS setup initially.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
from datasets import load_dataset
import uvicorn
from tqdm import tqdm

# Configuration
CURRENT_DIR = Path(__file__).parent
DATASETS_DIR = CURRENT_DIR.parent / "datasets"
PYTHON_ENV_DIR = CURRENT_DIR.parent / "python-env"

# FastAPI app
app = FastAPI(
    title="RAG Evaluation Service",
    description="Python backend for RAG evaluation metrics and dataset management",
    version="1.0.0"
)

# Pydantic models for API
class EvaluationRequest(BaseModel):
    query: str
    retrieved_contexts: List[str]
    generated_answer: str
    ground_truth: Optional[str] = None
    metrics: List[str] = ["basic_relevance", "context_utilization", "answer_completeness"]

class DatasetDownloadRequest(BaseModel):
    dataset_name: str
    subset: Optional[str] = None
    split: str = "train"
    max_samples: Optional[int] = None

class EvaluationResult(BaseModel):
    query: str
    metrics: Dict[str, float]
    details: Dict[str, Any]

class DatasetInfo(BaseModel):
    name: str
    size: int
    splits: List[str]
    features: Dict[str, str]

# Basic evaluation metrics (without RAGAS dependency)
class BasicRAGMetrics:
    """Basic RAG evaluation metrics that don't require ML models"""
    
    @staticmethod
    def calculate_basic_relevance(query: str, contexts: List[str]) -> float:
        """Calculate basic relevance score using keyword overlap"""
        query_words = set(query.lower().split())
        if not query_words:
            return 0.0
            
        total_relevance = 0.0
        for context in contexts:
            context_words = set(context.lower().split())
            if context_words:
                overlap = len(query_words.intersection(context_words))
                relevance = overlap / len(query_words.union(context_words))
                total_relevance += relevance
        
        return total_relevance / len(contexts) if contexts else 0.0
    
    @staticmethod
    def calculate_context_utilization(contexts: List[str], answer: str) -> float:
        """Calculate how well the answer utilizes the retrieved contexts"""
        if not contexts or not answer:
            return 0.0
            
        answer_words = set(answer.lower().split())
        context_words = set()
        for context in contexts:
            context_words.update(context.lower().split())
        
        if not context_words:
            return 0.0
            
        utilization = len(answer_words.intersection(context_words)) / len(context_words)
        return min(utilization, 1.0)  # Cap at 1.0
    
    @staticmethod
    def calculate_answer_completeness(query: str, answer: str) -> float:
        """Calculate completeness based on answer length and query coverage"""
        if not query or not answer:
            return 0.0
            
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        
        # Basic completeness heuristic
        coverage = len(query_words.intersection(answer_words)) / len(query_words)
        length_factor = min(len(answer.split()) / 20, 1.0)  # Assume 20 words is "complete"
        
        return (coverage + length_factor) / 2

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "RAG Evaluation Service"}

@app.get("/datasets")
async def list_available_datasets():
    """List available datasets for download"""
    available_datasets = [
        {
            "name": "BeIR/nq",
            "description": "Natural Questions from BEIR benchmark",
            "type": "question-answering",
            "size": "~100k samples"
        },
        {
            "name": "BeIR/scidocs",
            "description": "Scientific document retrieval from BEIR",
            "type": "document-retrieval", 
            "size": "~25k samples"
        },
        {
            "name": "yixuantt/MultiHopRAG",
            "description": "Multi-document reasoning dataset",
            "type": "multi-hop-qa",
            "size": "~2.5k samples"
        },
        {
            "name": "TIGER-Lab/M-BEIR",
            "description": "Multimodal BEIR benchmark",
            "type": "multimodal-retrieval",
            "size": "~1.5M queries"
        }
    ]
    return {"available_datasets": available_datasets}

@app.post("/datasets/download")
async def download_dataset(request: DatasetDownloadRequest):
    """Download and prepare a dataset for evaluation"""
    try:
        # Create dataset directory if it doesn't exist
        dataset_dir = DATASETS_DIR / request.dataset_name.replace('/', '_')
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # Download dataset using HuggingFace datasets
        print(f"Downloading dataset: {request.dataset_name}")
        
        # Handle different dataset formats
        if request.dataset_name.startswith("BeIR/"):
            dataset = load_dataset(request.dataset_name, split=request.split)
        elif request.dataset_name == "yixuantt/MultiHopRAG":
            dataset = load_dataset(request.dataset_name, "MultiHopRAG", split=request.split)
        else:
            dataset = load_dataset(request.dataset_name, split=request.split)
        
        # Limit samples if requested
        if request.max_samples and len(dataset) > request.max_samples:
            dataset = dataset.select(range(request.max_samples))
        
        # Save to local directory
        output_path = dataset_dir / f"{request.split}.jsonl"
        dataset.to_json(output_path)
        
        # Create metadata file
        metadata = {
            "dataset_name": request.dataset_name,
            "split": request.split,
            "samples": len(dataset),
            "features": list(dataset.features.keys()),
            "downloaded_at": pd.Timestamp.now().isoformat(),
            "local_path": str(output_path)
        }
        
        metadata_path = dataset_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            "status": "success",
            "dataset": request.dataset_name,
            "samples": len(dataset),
            "local_path": str(output_path),
            "metadata_path": str(metadata_path)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download dataset: {str(e)}")

@app.post("/evaluate")
async def evaluate_rag_response(request: EvaluationRequest) -> EvaluationResult:
    """Evaluate a RAG response using basic metrics"""
    try:
        metrics_calculator = BasicRAGMetrics()
        results = {}
        details = {}
        
        # Calculate requested metrics
        if "basic_relevance" in request.metrics:
            relevance = metrics_calculator.calculate_basic_relevance(
                request.query, request.retrieved_contexts
            )
            results["basic_relevance"] = relevance
            details["basic_relevance"] = {
                "description": "Keyword overlap between query and contexts",
                "range": "[0, 1]",
                "interpretation": "Higher is better"
            }
        
        if "context_utilization" in request.metrics:
            utilization = metrics_calculator.calculate_context_utilization(
                request.retrieved_contexts, request.generated_answer
            )
            results["context_utilization"] = utilization
            details["context_utilization"] = {
                "description": "How well the answer uses retrieved contexts",
                "range": "[0, 1]", 
                "interpretation": "Higher is better"
            }
        
        if "answer_completeness" in request.metrics:
            completeness = metrics_calculator.calculate_answer_completeness(
                request.query, request.generated_answer
            )
            results["answer_completeness"] = completeness
            details["answer_completeness"] = {
                "description": "Completeness of answer relative to query",
                "range": "[0, 1]",
                "interpretation": "Higher is better"
            }
        
        return EvaluationResult(
            query=request.query,
            metrics=results,
            details=details
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.get("/datasets/local")
async def list_local_datasets():
    """List locally downloaded datasets"""
    local_datasets = []
    
    if DATASETS_DIR.exists():
        for dataset_dir in DATASETS_DIR.iterdir():
            if dataset_dir.is_dir():
                metadata_path = dataset_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    local_datasets.append(metadata)
                else:
                    # Basic info for datasets without metadata
                    local_datasets.append({
                        "dataset_name": dataset_dir.name,
                        "local_path": str(dataset_dir),
                        "status": "no_metadata"
                    })
    
    return {"local_datasets": local_datasets}

@app.post("/batch-evaluate")
async def batch_evaluate_dataset(dataset_name: str, metrics: List[str] = None):
    """Evaluate a complete dataset using specified metrics"""
    try:
        if not metrics:
            metrics = ["basic_relevance", "context_utilization", "answer_completeness"]
        
        # Load local dataset
        dataset_dir = DATASETS_DIR / dataset_name.replace('/', '_')
        data_file = dataset_dir / "train.jsonl"
        
        if not data_file.exists():
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_name} not found locally")
        
        # Load dataset
        df = pd.read_json(data_file, lines=True)
        results = []
        
        # Process each sample (limit to first 100 for demo)
        sample_size = min(len(df), 100)
        
        for idx, row in tqdm(df.head(sample_size).iterrows(), total=sample_size):
            # Extract fields based on dataset format
            if 'query' in row:
                query = row['query']
            elif 'question' in row:
                query = row['question']
            else:
                query = str(row.get('text', ''))[:200]  # Fallback
                
            # Mock contexts and answers for datasets without these fields
            contexts = [str(row.get('context', row.get('passage', 'No context available')))]
            answer = str(row.get('answer', row.get('response', 'No answer available')))
            
            # Create evaluation request
            eval_request = EvaluationRequest(
                query=query,
                retrieved_contexts=contexts,
                generated_answer=answer,
                metrics=metrics
            )
            
            # Evaluate
            result = await evaluate_rag_response(eval_request)
            results.append({
                "sample_id": idx,
                "query": query,
                "metrics": result.metrics
            })
        
        # Calculate aggregate statistics
        metrics_df = pd.DataFrame([r["metrics"] for r in results])
        aggregates = {
            "mean": metrics_df.mean().to_dict(),
            "std": metrics_df.std().to_dict(),
            "min": metrics_df.min().to_dict(),
            "max": metrics_df.max().to_dict()
        }
        
        return {
            "dataset": dataset_name,
            "evaluated_samples": len(results),
            "individual_results": results[:10],  # Return first 10 individual results
            "aggregate_metrics": aggregates,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch evaluation failed: {str(e)}")

if __name__ == "__main__":
    print("Starting RAG Evaluation Service...")
    print(f"Datasets directory: {DATASETS_DIR}")
    print(f"Python environment: {PYTHON_ENV_DIR}")
    
    # Create necessary directories
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Start server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )