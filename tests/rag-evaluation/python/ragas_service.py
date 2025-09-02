#!/usr/bin/env python3
"""
RAGAS-based RAG Evaluation Service
Provides proper RAG evaluation using RAGAS with LLM-based metrics
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
from datasets import load_dataset, Dataset
import uvicorn
from tqdm import tqdm

# RAGAS imports
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy, 
    context_precision,
    context_recall,
    answer_correctness
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Configuration
CURRENT_DIR = Path(__file__).parent
DATASETS_DIR = CURRENT_DIR.parent / "datasets"
GROUND_TRUTH_DIR = CURRENT_DIR.parent / "ground_truth"

# Create directories
GROUND_TRUTH_DIR.mkdir(exist_ok=True)

# FastAPI app
app = FastAPI(
    title="RAGAS RAG Evaluation Service",
    description="Professional RAG evaluation using RAGAS with LLM-based metrics",
    version="2.0.0"
)

# Pydantic models
class RAGASEvaluationRequest(BaseModel):
    question: str
    contexts: List[str]
    answer: str
    ground_truth: Optional[str] = None
    metrics: List[str] = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

class GroundTruthEntry(BaseModel):
    question: str
    contexts: List[str]
    answer: str
    ground_truth: str
    source: str = "manual"

class RAGASEvaluationResult(BaseModel):
    question: str
    metrics: Dict[str, float]
    evaluation_details: Dict[str, Any]

class GroundTruthDataset(BaseModel):
    name: str
    entries: List[GroundTruthEntry]
    description: str = ""

# Initialize RAGAS with OpenAI (you can switch to other LLMs)
def get_llm_and_embeddings():
    """Initialize LLM and embeddings for RAGAS"""
    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Try to read from a local file
        key_file = CURRENT_DIR.parent / ".env"
        if key_file.exists():
            with open(key_file) as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        os.environ["OPENAI_API_KEY"] = api_key
                        break
    
    if not api_key:
        raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable or create .env file")
    
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    embeddings = OpenAIEmbeddings()
    return llm, embeddings

# Ground truth data for evaluation
DEFAULT_GROUND_TRUTH = [
    {
        "question": "What is the capital of France?",
        "contexts": ["France is a country in Western Europe.", "Paris is the capital and most populous city of France."],
        "answer": "The capital of France is Paris.",
        "ground_truth": "Paris"
    },
    {
        "question": "How does photosynthesis work?",
        "contexts": [
            "Photosynthesis is the process by which plants convert light energy into chemical energy.",
            "During photosynthesis, plants use sunlight, carbon dioxide, and water to produce glucose and oxygen.",
            "Chlorophyll in plant leaves captures sunlight for the photosynthesis process."
        ],
        "answer": "Photosynthesis is the process where plants use sunlight, carbon dioxide, and water to create glucose and oxygen, with chlorophyll capturing the light energy.",
        "ground_truth": "Photosynthesis converts light energy to chemical energy using sunlight, CO2, and water to produce glucose and oxygen."
    },
    {
        "question": "What causes earthquakes?",
        "contexts": [
            "Earthquakes are caused by the sudden movement of tectonic plates in the Earth's crust.",
            "The Earth's crust is made up of several large plates that move slowly over time.",
            "When these plates get stuck and then suddenly slip, they release energy in the form of seismic waves."
        ],
        "answer": "Earthquakes are caused by the sudden movement and slipping of tectonic plates in the Earth's crust, which releases energy as seismic waves.",
        "ground_truth": "Earthquakes result from sudden movement of tectonic plates releasing seismic energy."
    },
    {
        "question": "What is artificial intelligence?",
        "contexts": [
            "Artificial Intelligence (AI) refers to computer systems that can perform tasks typically requiring human intelligence.",
            "AI systems can learn, reason, and make decisions based on data and algorithms.",
            "Machine learning is a subset of AI that enables systems to learn from data without explicit programming."
        ],
        "answer": "Artificial Intelligence is computer systems that perform human-like tasks such as learning, reasoning, and decision-making using data and algorithms.",
        "ground_truth": "AI refers to computer systems that simulate human intelligence through learning, reasoning, and decision-making."
    },
    {
        "question": "How do vaccines work?",
        "contexts": [
            "Vaccines work by training the immune system to recognize and fight specific diseases.",
            "They contain weakened or dead parts of the disease-causing organism or blueprints for making such parts.",
            "When vaccinated, the immune system produces antibodies and remembers how to fight the disease in the future."
        ],
        "answer": "Vaccines train the immune system by exposing it to weakened disease parts, causing the body to produce antibodies and develop immunity for future protection.",
        "ground_truth": "Vaccines stimulate immune response by introducing weakened pathogens, creating antibodies and immunological memory."
    }
]

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "RAGAS RAG Evaluation Service", "version": "2.0.0"}

@app.post("/evaluate")
async def evaluate_with_ragas(request: RAGASEvaluationRequest) -> RAGASEvaluationResult:
    """Evaluate RAG response using RAGAS metrics"""
    try:
        # Initialize LLM and embeddings
        llm, embeddings = get_llm_and_embeddings()
        
        # Create dataset for RAGAS
        data = {
            "question": [request.question],
            "contexts": [request.contexts],
            "answer": [request.answer]
        }
        
        if request.ground_truth:
            data["ground_truth"] = [request.ground_truth]
        
        dataset = Dataset.from_dict(data)
        
        # Select metrics
        available_metrics = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
            "answer_correctness": answer_correctness
        }
        
        selected_metrics = []
        for metric_name in request.metrics:
            if metric_name in available_metrics:
                selected_metrics.append(available_metrics[metric_name])
            else:
                print(f"Warning: Unknown metric '{metric_name}', skipping")
        
        if not selected_metrics:
            raise HTTPException(status_code=400, detail="No valid metrics specified")
        
        # Run evaluation
        result = evaluate(
            dataset=dataset,
            metrics=selected_metrics,
            llm=llm,
            embeddings=embeddings
        )
        
        # Extract results - RAGAS returns DataFrame-like structure
        metrics_results = {}
        evaluation_details = {
            "evaluation_framework": "RAGAS",
            "llm_model": "gpt-4o-mini",
            "embeddings_model": "text-embedding-3-small", 
            "evaluated_at": pd.Timestamp.now().isoformat()
        }
        
        # Convert result to dict if it's a Dataset
        if hasattr(result, 'to_pandas'):
            result_df = result.to_pandas()
            for metric_name in request.metrics:
                if metric_name in result_df.columns:
                    score = result_df[metric_name].iloc[0]  # Get first (and only) score
                    metrics_results[metric_name] = float(score)
        else:
            # Fallback for direct dict access
            for metric_name in request.metrics:
                if metric_name in result:
                    score = result[metric_name]
                    if isinstance(score, (list, np.ndarray)) and len(score) > 0:
                        metrics_results[metric_name] = float(score[0])
                    else:
                        metrics_results[metric_name] = float(score)
        
        return RAGASEvaluationResult(
            question=request.question,
            metrics=metrics_results,
            evaluation_details=evaluation_details
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAGAS evaluation failed: {str(e)}")

@app.get("/ground-truth")
async def get_ground_truth_data():
    """Get available ground truth data for testing"""
    ground_truth_file = GROUND_TRUTH_DIR / "default_qa.json"
    
    if not ground_truth_file.exists():
        # Create default ground truth file
        with open(ground_truth_file, 'w') as f:
            json.dump(DEFAULT_GROUND_TRUTH, f, indent=2)
    
    with open(ground_truth_file) as f:
        data = json.load(f)
    
    return {
        "ground_truth_entries": len(data),
        "data": data,
        "file_path": str(ground_truth_file)
    }

@app.post("/ground-truth")
async def add_ground_truth_entry(entry: GroundTruthEntry):
    """Add a new ground truth entry"""
    ground_truth_file = GROUND_TRUTH_DIR / "default_qa.json"
    
    # Load existing data
    if ground_truth_file.exists():
        with open(ground_truth_file) as f:
            data = json.load(f)
    else:
        data = []
    
    # Add new entry
    data.append({
        "question": entry.question,
        "contexts": entry.contexts,
        "answer": entry.answer,
        "ground_truth": entry.ground_truth,
        "source": entry.source
    })
    
    # Save updated data
    with open(ground_truth_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return {"status": "success", "message": f"Added ground truth entry. Total entries: {len(data)}"}

@app.post("/batch-evaluate")
async def batch_evaluate_ground_truth(metrics: List[str] = None):
    """Run batch evaluation on ground truth dataset"""
    try:
        if not metrics:
            metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        
        # Load ground truth data
        ground_truth_file = GROUND_TRUTH_DIR / "default_qa.json"
        if not ground_truth_file.exists():
            raise HTTPException(status_code=404, detail="No ground truth data found")
        
        with open(ground_truth_file) as f:
            ground_truth_data = json.load(f)
        
        if not ground_truth_data:
            raise HTTPException(status_code=400, detail="Ground truth dataset is empty")
        
        # Initialize LLM and embeddings
        llm, embeddings = get_llm_and_embeddings()
        
        # Prepare data for RAGAS
        questions = [item["question"] for item in ground_truth_data]
        contexts = [item["contexts"] for item in ground_truth_data]
        answers = [item["answer"] for item in ground_truth_data]
        ground_truths = [item["ground_truth"] for item in ground_truth_data]
        
        dataset = Dataset.from_dict({
            "question": questions,
            "contexts": contexts,
            "answer": answers,
            "ground_truth": ground_truths
        })
        
        # Select metrics
        available_metrics = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
            "answer_correctness": answer_correctness
        }
        
        selected_metrics = [available_metrics[m] for m in metrics if m in available_metrics]
        
        # Run batch evaluation
        result = evaluate(
            dataset=dataset,
            metrics=selected_metrics,
            llm=llm,
            embeddings=embeddings
        )
        
        # Calculate aggregate statistics - Handle RAGAS Dataset result
        aggregate_results = {}
        individual_results = []
        
        # Convert result to pandas DataFrame for easier processing
        if hasattr(result, 'to_pandas'):
            result_df = result.to_pandas()
            
            for metric_name in metrics:
                if metric_name in result_df.columns:
                    scores = result_df[metric_name].values
                    aggregate_results[metric_name] = {
                        "mean": float(np.mean(scores)),
                        "std": float(np.std(scores)),
                        "min": float(np.min(scores)),
                        "max": float(np.max(scores))
                    }
                    
                    # Individual results
                    for i, score in enumerate(scores):
                        if len(individual_results) <= i:
                            individual_results.append({
                                "question_id": i,
                                "question": questions[i],
                                "metrics": {}
                            })
                        individual_results[i]["metrics"][metric_name] = float(score)
        else:
            # Fallback for direct dict access
            for metric_name in metrics:
                if metric_name in result:
                    scores = result[metric_name]
                    if isinstance(scores, (list, np.ndarray)):
                        aggregate_results[metric_name] = {
                            "mean": float(np.mean(scores)),
                            "std": float(np.std(scores)),
                            "min": float(np.min(scores)),
                            "max": float(np.max(scores))
                        }
                        
                        # Individual results
                        for i, score in enumerate(scores):
                            if len(individual_results) <= i:
                                individual_results.append({
                                    "question_id": i,
                                    "question": questions[i],
                                    "metrics": {}
                                })
                            individual_results[i]["metrics"][metric_name] = float(score)
        
        return {
            "evaluation_summary": {
                "dataset": "ground_truth",
                "samples_evaluated": len(ground_truth_data),
                "metrics_used": metrics,
                "framework": "RAGAS",
                "timestamp": pd.Timestamp.now().isoformat()
            },
            "aggregate_results": aggregate_results,
            "individual_results": individual_results[:5],  # Return first 5 for brevity
            "total_entries": len(individual_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch evaluation failed: {str(e)}")

@app.post("/compare-systems")
async def compare_rag_systems(system_a_responses: List[str], system_b_responses: List[str]):
    """Compare two RAG systems using ground truth data"""
    try:
        # Load ground truth
        ground_truth_file = GROUND_TRUTH_DIR / "default_qa.json"
        with open(ground_truth_file) as f:
            ground_truth_data = json.load(f)
        
        if len(system_a_responses) != len(system_b_responses) or len(system_a_responses) != len(ground_truth_data):
            raise HTTPException(status_code=400, detail="Response arrays must match ground truth length")
        
        llm, embeddings = get_llm_and_embeddings()
        
        # Evaluate System A
        dataset_a = Dataset.from_dict({
            "question": [item["question"] for item in ground_truth_data],
            "contexts": [item["contexts"] for item in ground_truth_data],
            "answer": system_a_responses,
            "ground_truth": [item["ground_truth"] for item in ground_truth_data]
        })
        
        result_a = evaluate(
            dataset=dataset_a,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=llm,
            embeddings=embeddings
        )
        
        # Evaluate System B
        dataset_b = Dataset.from_dict({
            "question": [item["question"] for item in ground_truth_data],
            "contexts": [item["contexts"] for item in ground_truth_data],
            "answer": system_b_responses,
            "ground_truth": [item["ground_truth"] for item in ground_truth_data]
        })
        
        result_b = evaluate(
            dataset=dataset_b,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=llm,
            embeddings=embeddings
        )
        
        # Compare results
        comparison = {}
        for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            if metric in result_a and metric in result_b:
                score_a = np.mean(result_a[metric])
                score_b = np.mean(result_b[metric])
                comparison[metric] = {
                    "system_a": float(score_a),
                    "system_b": float(score_b),
                    "difference": float(score_b - score_a),
                    "winner": "System B" if score_b > score_a else "System A" if score_a > score_b else "Tie"
                }
        
        return {
            "comparison_results": comparison,
            "overall_winner": max(comparison.items(), key=lambda x: abs(x[1]["difference"]))[1]["winner"],
            "evaluated_samples": len(ground_truth_data),
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System comparison failed: {str(e)}")

if __name__ == "__main__":
    print("Starting RAGAS RAG Evaluation Service...")
    print(f"Ground truth directory: {GROUND_TRUTH_DIR}")
    print(f"Datasets directory: {DATASETS_DIR}")
    
    # Create necessary directories
    GROUND_TRUTH_DIR.mkdir(exist_ok=True)
    
    # Check OpenAI API key
    try:
        get_llm_and_embeddings()
        print("OpenAI API key found and configured")
    except ValueError as e:
        print(f"Warning: {e}")
        print("Some features will be limited without proper API configuration")
    
    # Start server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,  # Different port than the old service
        log_level="info",
        reload=False
    )