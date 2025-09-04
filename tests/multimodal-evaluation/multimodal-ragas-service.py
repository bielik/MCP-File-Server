#!/usr/bin/env python3
"""
Multimodal RAGAS Evaluation Service
Extended evaluation framework for multimodal document processing and cross-modal search
Integrates with existing RAGAS service and adds multimodal-specific quality metrics
"""

import os
import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import logging
import time
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import uvicorn
from PIL import Image
import torch
from sentence_transformers import SentenceTransformer
import requests

# Configuration
SERVICE_PORT = 8004
RAGAS_SERVICE_URL = "http://127.0.0.1:8001"
MCLIP_SERVICE_URL = "http://127.0.0.1:8002"
DOCLING_SERVICE_URL = "http://127.0.0.1:8003"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model for similarity calculations
similarity_model = None

# Pydantic models for multimodal evaluation
class MultimodalEvaluationRequest(BaseModel):
    """Request for comprehensive multimodal evaluation"""
    query: str
    retrieved_contexts: List[str]
    retrieved_images: List[Dict[str, Any]] = Field(default_factory=list)
    generated_answer: str
    ground_truth: Optional[str] = None
    cross_modal_pairs: List[Dict[str, Any]] = Field(default_factory=list)
    evaluation_types: List[str] = Field(default=['text_quality', 'image_relevance', 'cross_modal_consistency', 'multimodal_faithfulness'])

class CrossModalPair(BaseModel):
    """Text-image pair for cross-modal evaluation"""
    text_content: str
    image_path: Optional[str] = None
    image_description: Optional[str] = None
    relationship_type: str  # 'caption', 'reference', 'illustration'
    confidence: float = Field(ge=0.0, le=1.0)

class MultimodalEvaluationResult(BaseModel):
    """Comprehensive multimodal evaluation results"""
    query: str
    
    # Core RAGAS metrics
    ragas_metrics: Dict[str, float] = Field(default_factory=dict)
    
    # Multimodal-specific metrics
    image_relevance: float = Field(ge=0.0, le=1.0)
    cross_modal_consistency: float = Field(ge=0.0, le=1.0)
    multimodal_faithfulness: float = Field(ge=0.0, le=1.0)
    visual_grounding: float = Field(ge=0.0, le=1.0)
    content_coverage: float = Field(ge=0.0, le=1.0)
    
    # Quality assessment
    extraction_quality: Dict[str, float] = Field(default_factory=dict)
    relationship_quality: Dict[str, float] = Field(default_factory=dict)
    
    # Detailed breakdowns
    detailed_scores: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    
    # Processing metadata
    evaluation_time: float
    models_used: List[str] = Field(default_factory=list)

class DocumentProcessingEvaluationRequest(BaseModel):
    """Evaluation request for document processing pipeline"""
    document_path: str
    processing_result: Dict[str, Any]
    ground_truth_annotations: Optional[Dict[str, Any]] = None
    evaluation_aspects: List[str] = Field(default=['extraction_completeness', 'chunking_quality', 'embedding_quality', 'relationship_accuracy'])

class DocumentProcessingEvaluationResult(BaseModel):
    """Document processing evaluation results"""
    document_path: str
    
    # Processing quality metrics
    extraction_completeness: float = Field(ge=0.0, le=1.0)
    chunking_quality: float = Field(ge=0.0, le=1.0)
    embedding_quality: float = Field(ge=0.0, le=1.0)
    relationship_accuracy: float = Field(ge=0.0, le=1.0)
    
    # Content analysis
    text_extraction_score: float = Field(ge=0.0, le=1.0)
    image_extraction_score: float = Field(ge=0.0, le=1.0)
    metadata_completeness: float = Field(ge=0.0, le=1.0)
    
    # Quality breakdowns
    detailed_analysis: Dict[str, Any] = Field(default_factory=dict)
    issues_found: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    
    # Overall scores
    overall_quality_score: float = Field(ge=0.0, le=1.0)
    processing_efficiency: float = Field(ge=0.0, le=1.0)

class SearchEvaluationRequest(BaseModel):
    """Evaluation request for multimodal search results"""
    query: str
    search_results: List[Dict[str, Any]]
    search_type: str  # 'text', 'semantic', 'cross_modal', 'hybrid'
    ground_truth_relevant_ids: Optional[List[str]] = None
    evaluation_metrics: List[str] = Field(default=['relevance', 'ranking_quality', 'diversity', 'cross_modal_accuracy'])

class SearchEvaluationResult(BaseModel):
    """Search evaluation results"""
    query: str
    search_type: str
    
    # Information retrieval metrics
    precision_at_k: Dict[int, float] = Field(default_factory=dict)
    recall_at_k: Dict[int, float] = Field(default_factory=dict)
    map_score: float = Field(ge=0.0, le=1.0)  # Mean Average Precision
    ndcg_score: float = Field(ge=0.0, le=1.0)  # Normalized DCG
    
    # Multimodal-specific metrics
    cross_modal_accuracy: float = Field(ge=0.0, le=1.0)
    result_diversity: float = Field(ge=0.0, le=1.0)
    visual_relevance: float = Field(ge=0.0, le=1.0)
    
    # Quality analysis
    ranking_quality: float = Field(ge=0.0, le=1.0)
    semantic_consistency: float = Field(ge=0.0, le=1.0)
    
    # Detailed analysis
    per_result_scores: List[Dict[str, float]] = Field(default_factory=list)
    quality_issues: List[str] = Field(default_factory=list)
    optimization_suggestions: List[str] = Field(default_factory=list)

# Service initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global similarity_model
    
    # Startup
    logger.info("🚀 Starting Multimodal RAGAS Evaluation Service")
    
    try:
        # Initialize similarity model for evaluations
        logger.info("Loading similarity model...")
        similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Similarity model loaded")
        
        # Test connections to other services
        await test_service_connections()
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize service: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Multimodal RAGAS Evaluation Service")

async def test_service_connections():
    """Test connections to required services"""
    services = [
        ("RAGAS Service", f"{RAGAS_SERVICE_URL}/health"),
        ("M-CLIP Service", f"{MCLIP_SERVICE_URL}/health"),
        ("Docling Service", f"{DOCLING_SERVICE_URL}/health")
    ]
    
    for service_name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ {service_name} connection successful")
            else:
                logger.warning(f"⚠️ {service_name} returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ {service_name} connection failed: {e}")

# Evaluation classes
class MultimodalQualityEvaluator:
    """Evaluates multimodal content quality and consistency"""
    
    def __init__(self):
        self.similarity_model = similarity_model
    
    async def evaluate_image_relevance(self, query: str, images: List[Dict[str, Any]]) -> float:
        """Evaluate relevance of retrieved images to query"""
        if not images:
            return 0.0
        
        try:
            # Get query embedding
            query_response = requests.post(f"{MCLIP_SERVICE_URL}/embed/text", 
                                         json={"text": query}, timeout=10)
            if query_response.status_code != 200:
                return 0.5  # Default score if embedding fails
            
            query_embedding = query_response.json()["embedding"]
            relevance_scores = []
            
            for image in images:
                if image.get("image_path"):
                    # Get image embedding
                    img_response = requests.post(f"{MCLIP_SERVICE_URL}/embed/image",
                                               json={"image_path": image["image_path"]}, timeout=10)
                    if img_response.status_code == 200:
                        img_embedding = img_response.json()["embedding"]
                        # Calculate cosine similarity
                        similarity = self.cosine_similarity(query_embedding, img_embedding)
                        relevance_scores.append(similarity)
            
            return np.mean(relevance_scores) if relevance_scores else 0.0
            
        except Exception as e:
            logger.warning(f"Image relevance evaluation failed: {e}")
            return 0.5
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    
    def evaluate_cross_modal_consistency(self, cross_modal_pairs: List[Dict[str, Any]]) -> float:
        """Evaluate consistency between text and image pairs"""
        if not cross_modal_pairs:
            return 1.0
        
        consistency_scores = []
        
        for pair in cross_modal_pairs:
            if pair.get("relationship_type") == "caption":
                # High weight for caption consistency
                score = pair.get("confidence", 0.5) * 1.2
            elif pair.get("relationship_type") == "reference":
                # Medium weight for references
                score = pair.get("confidence", 0.5) * 1.0
            else:
                # Lower weight for other relationships
                score = pair.get("confidence", 0.5) * 0.8
            
            consistency_scores.append(min(score, 1.0))
        
        return np.mean(consistency_scores) if consistency_scores else 0.5
    
    def evaluate_multimodal_faithfulness(self, answer: str, contexts: List[str], images: List[Dict[str, Any]]) -> float:
        """Evaluate faithfulness of answer to multimodal context"""
        try:
            # Combine text contexts and image descriptions
            all_contexts = contexts.copy()
            for image in images:
                if image.get("extracted_text"):
                    all_contexts.append(f"Image content: {image['extracted_text']}")
                if image.get("caption"):
                    all_contexts.append(f"Image caption: {image['caption']}")
            
            if not all_contexts:
                return 0.0
            
            # Calculate semantic similarity between answer and combined contexts
            if self.similarity_model:
                answer_embedding = self.similarity_model.encode([answer])
                context_embeddings = self.similarity_model.encode(all_contexts)
                
                # Find maximum similarity with any context
                similarities = []
                for context_emb in context_embeddings:
                    sim = np.dot(answer_embedding[0], context_emb) / (
                        np.linalg.norm(answer_embedding[0]) * np.linalg.norm(context_emb)
                    )
                    similarities.append(sim)
                
                return float(np.max(similarities))
            
            return 0.7  # Default if model unavailable
            
        except Exception as e:
            logger.warning(f"Multimodal faithfulness evaluation failed: {e}")
            return 0.5
    
    def evaluate_visual_grounding(self, answer: str, images: List[Dict[str, Any]]) -> float:
        """Evaluate how well the answer is grounded in visual content"""
        if not images:
            return 1.0  # Perfect if no images to ground
        
        visual_references = 0
        total_visual_content = 0
        
        for image in images:
            total_visual_content += 1
            
            # Check for visual references in answer
            visual_keywords = ["figure", "image", "chart", "graph", "diagram", "illustration", "shown", "depicted"]
            if any(keyword in answer.lower() for keyword in visual_keywords):
                visual_references += 1
            
            # Check for specific image content references
            if image.get("extracted_text"):
                if any(word in answer.lower() for word in image["extracted_text"].lower().split()[:10]):
                    visual_references += 0.5
        
        return min(visual_references / total_visual_content, 1.0) if total_visual_content > 0 else 1.0
    
    def evaluate_content_coverage(self, answer: str, contexts: List[str], images: List[Dict[str, Any]]) -> float:
        """Evaluate how well the answer covers available content"""
        total_content_elements = len(contexts) + len(images)
        if total_content_elements == 0:
            return 1.0
        
        covered_elements = 0
        answer_words = set(answer.lower().split())
        
        # Check text context coverage
        for context in contexts:
            context_words = set(context.lower().split())
            overlap = len(answer_words.intersection(context_words))
            if overlap > 3:  # Threshold for meaningful coverage
                covered_elements += 1
        
        # Check image content coverage
        for image in images:
            if image.get("extracted_text"):
                image_words = set(image["extracted_text"].lower().split())
                overlap = len(answer_words.intersection(image_words))
                if overlap > 1:
                    covered_elements += 0.5
        
        return min(covered_elements / total_content_elements, 1.0)

class DocumentProcessingEvaluator:
    """Evaluates document processing pipeline quality"""
    
    def evaluate_extraction_completeness(self, processing_result: Dict[str, Any]) -> float:
        """Evaluate completeness of content extraction"""
        scores = []
        
        # Text extraction completeness
        text_chunks = processing_result.get("text_chunks", [])
        if text_chunks:
            avg_chunk_size = np.mean([len(chunk.get("content", "")) for chunk in text_chunks])
            text_score = min(avg_chunk_size / 500, 1.0)  # Assume 500 chars is good chunk size
            scores.append(text_score)
        
        # Image extraction completeness
        images = processing_result.get("images", [])
        metadata = processing_result.get("metadata", {})
        total_pages = metadata.get("total_pages", 1)
        
        if images:
            images_per_page = len(images) / total_pages
            image_score = min(images_per_page / 2, 1.0)  # Assume 2 images/page is good
            scores.append(image_score)
        
        # Metadata completeness
        metadata_fields = ["title", "authors", "total_pages", "word_count"]
        metadata_completeness = sum(1 for field in metadata_fields if metadata.get(field)) / len(metadata_fields)
        scores.append(metadata_completeness)
        
        return np.mean(scores) if scores else 0.5
    
    def evaluate_chunking_quality(self, text_chunks: List[Dict[str, Any]]) -> float:
        """Evaluate quality of text chunking"""
        if not text_chunks:
            return 0.0
        
        scores = []
        
        # Check chunk size consistency
        chunk_sizes = [len(chunk.get("content", "")) for chunk in text_chunks]
        if chunk_sizes:
            size_variance = np.var(chunk_sizes)
            size_score = max(0, 1 - size_variance / 100000)  # Penalize high variance
            scores.append(size_score)
        
        # Check for sentence integrity (chunks shouldn't break mid-sentence)
        sentence_integrity_score = 0
        for chunk in text_chunks:
            content = chunk.get("content", "")
            if content.endswith(('.', '!', '?')) or content.endswith('\n'):
                sentence_integrity_score += 1
        
        if text_chunks:
            scores.append(sentence_integrity_score / len(text_chunks))
        
        # Check overlap appropriateness
        # This would require more sophisticated analysis in production
        scores.append(0.8)  # Default overlap score
        
        return np.mean(scores) if scores else 0.5
    
    def evaluate_relationship_accuracy(self, relationships: List[Dict[str, Any]]) -> float:
        """Evaluate accuracy of identified relationships"""
        if not relationships:
            return 1.0  # Perfect if no relationships to evaluate
        
        # Evaluate relationship confidence scores
        confidences = [rel.get("confidence", 0.5) for rel in relationships]
        avg_confidence = np.mean(confidences)
        
        # Check relationship type distribution
        relationship_types = [rel.get("relationship_type", "") for rel in relationships]
        type_counts = {}
        for rel_type in relationship_types:
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
        
        # Penalize if too many low-quality relationships
        caption_ratio = type_counts.get("caption", 0) / len(relationships)
        reference_ratio = type_counts.get("reference", 0) / len(relationships)
        
        # Good balance of relationship types
        balance_score = 1.0 - abs(0.3 - caption_ratio) - abs(0.4 - reference_ratio)
        balance_score = max(0, balance_score)
        
        return (avg_confidence + balance_score) / 2

class SearchQualityEvaluator:
    """Evaluates multimodal search quality"""
    
    def evaluate_precision_recall(self, search_results: List[Dict[str, Any]], 
                                 relevant_ids: List[str]) -> Dict[str, Any]:
        """Calculate precision and recall at different k values"""
        if not relevant_ids:
            return {"precision_at_k": {}, "recall_at_k": {}, "map_score": 0.0}
        
        result_ids = [result.get("node_id", "") for result in search_results]
        relevant_set = set(relevant_ids)
        
        precision_at_k = {}
        recall_at_k = {}
        
        for k in [1, 3, 5, 10]:
            if k <= len(result_ids):
                top_k_ids = set(result_ids[:k])
                relevant_in_top_k = len(top_k_ids.intersection(relevant_set))
                
                precision_at_k[k] = relevant_in_top_k / k
                recall_at_k[k] = relevant_in_top_k / len(relevant_set)
        
        # Calculate MAP (simplified)
        map_score = precision_at_k.get(5, 0.0)  # Use P@5 as approximation
        
        return {
            "precision_at_k": precision_at_k,
            "recall_at_k": recall_at_k,
            "map_score": map_score
        }
    
    def evaluate_result_diversity(self, search_results: List[Dict[str, Any]]) -> float:
        """Evaluate diversity of search results"""
        if len(search_results) < 2:
            return 1.0
        
        # Check document diversity
        doc_ids = [result.get("metadata", {}).get("document_id", "") for result in search_results]
        unique_docs = len(set(doc_ids))
        doc_diversity = unique_docs / len(search_results)
        
        # Check content type diversity
        content_types = [result.get("metadata", {}).get("content_type", "text") for result in search_results]
        unique_types = len(set(content_types))
        type_diversity = min(unique_types / 3, 1.0)  # Max 3 types: text, image, table
        
        # Check page diversity
        pages = [result.get("metadata", {}).get("page_number", 1) for result in search_results]
        unique_pages = len(set(pages))
        page_diversity = min(unique_pages / 5, 1.0)  # Normalize by expected spread
        
        return (doc_diversity + type_diversity + page_diversity) / 3

# FastAPI app
app = FastAPI(
    title="Multimodal RAGAS Evaluation Service",
    description="Extended evaluation framework for multimodal document processing and search",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize evaluators
multimodal_evaluator = MultimodalQualityEvaluator()
document_evaluator = DocumentProcessingEvaluator()
search_evaluator = SearchQualityEvaluator()

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Multimodal RAGAS Evaluation",
        "models_loaded": similarity_model is not None,
        "connected_services": {
            "ragas": RAGAS_SERVICE_URL,
            "mclip": MCLIP_SERVICE_URL,
            "docling": DOCLING_SERVICE_URL
        }
    }

@app.post("/evaluate/multimodal", response_model=MultimodalEvaluationResult)
async def evaluate_multimodal_response(request: MultimodalEvaluationRequest):
    """Comprehensive evaluation of multimodal RAG response"""
    start_time = time.time()
    
    try:
        result = MultimodalEvaluationResult(
            query=request.query,
            evaluation_time=0,
            models_used=["multimodal_ragas", "m_clip", "sentence_transformers"]
        )
        
        # Get core RAGAS metrics
        if 'text_quality' in request.evaluation_types:
            try:
                ragas_response = requests.post(f"{RAGAS_SERVICE_URL}/evaluate", json={
                    "query": request.query,
                    "retrieved_contexts": request.retrieved_contexts,
                    "generated_answer": request.generated_answer,
                    "ground_truth": request.ground_truth,
                    "metrics": ["basic_relevance", "context_utilization", "answer_completeness"]
                }, timeout=30)
                
                if ragas_response.status_code == 200:
                    ragas_data = ragas_response.json()
                    result.ragas_metrics = ragas_data.get("metrics", {})
            except Exception as e:
                logger.warning(f"RAGAS evaluation failed: {e}")
                result.ragas_metrics = {"basic_relevance": 0.5, "context_utilization": 0.5, "answer_completeness": 0.5}
        
        # Multimodal-specific evaluations
        if 'image_relevance' in request.evaluation_types:
            result.image_relevance = await multimodal_evaluator.evaluate_image_relevance(
                request.query, request.retrieved_images
            )
        
        if 'cross_modal_consistency' in request.evaluation_types:
            result.cross_modal_consistency = multimodal_evaluator.evaluate_cross_modal_consistency(
                request.cross_modal_pairs
            )
        
        if 'multimodal_faithfulness' in request.evaluation_types:
            result.multimodal_faithfulness = multimodal_evaluator.evaluate_multimodal_faithfulness(
                request.generated_answer, request.retrieved_contexts, request.retrieved_images
            )
        
        # Additional quality metrics
        result.visual_grounding = multimodal_evaluator.evaluate_visual_grounding(
            request.generated_answer, request.retrieved_images
        )
        
        result.content_coverage = multimodal_evaluator.evaluate_content_coverage(
            request.generated_answer, request.retrieved_contexts, request.retrieved_images
        )
        
        # Generate recommendations
        result.recommendations = generate_multimodal_recommendations(result)
        
        result.evaluation_time = time.time() - start_time
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multimodal evaluation failed: {str(e)}")

@app.post("/evaluate/document-processing", response_model=DocumentProcessingEvaluationResult)
async def evaluate_document_processing(request: DocumentProcessingEvaluationRequest):
    """Evaluate document processing pipeline quality"""
    try:
        result = DocumentProcessingEvaluationResult(
            document_path=request.document_path
        )
        
        processing_result = request.processing_result
        
        # Evaluate different aspects
        if 'extraction_completeness' in request.evaluation_aspects:
            result.extraction_completeness = document_evaluator.evaluate_extraction_completeness(processing_result)
        
        if 'chunking_quality' in request.evaluation_aspects:
            text_chunks = processing_result.get("text_chunks", [])
            result.chunking_quality = document_evaluator.evaluate_chunking_quality(text_chunks)
        
        if 'relationship_accuracy' in request.evaluation_aspects:
            relationships = processing_result.get("relationships", [])
            result.relationship_accuracy = document_evaluator.evaluate_relationship_accuracy(relationships)
        
        # Content-specific scores
        result.text_extraction_score = min(len(processing_result.get("text_chunks", [])) / 10, 1.0)
        result.image_extraction_score = min(len(processing_result.get("images", [])) / 5, 1.0)
        
        metadata = processing_result.get("metadata", {})
        result.metadata_completeness = sum(1 for field in ["title", "authors", "total_pages"] 
                                         if metadata.get(field)) / 3
        
        # Calculate overall quality score
        scores = [
            result.extraction_completeness,
            result.chunking_quality,
            result.relationship_accuracy,
            result.text_extraction_score,
            result.image_extraction_score,
            result.metadata_completeness
        ]
        result.overall_quality_score = np.mean(scores)
        
        # Processing efficiency (based on processing time vs content)
        processing_time = processing_result.get("processing_time", 0)
        total_pages = metadata.get("total_pages", 1)
        result.processing_efficiency = min(total_pages / max(processing_time / 1000, 1), 1.0)
        
        # Generate improvement suggestions
        result.improvement_suggestions = generate_processing_suggestions(result)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing evaluation failed: {str(e)}")

@app.post("/evaluate/search", response_model=SearchEvaluationResult)
async def evaluate_search_quality(request: SearchEvaluationRequest):
    """Evaluate multimodal search quality"""
    try:
        result = SearchEvaluationResult(
            query=request.query,
            search_type=request.search_type
        )
        
        # Precision/Recall metrics
        if request.ground_truth_relevant_ids:
            ir_metrics = search_evaluator.evaluate_precision_recall(
                request.search_results, request.ground_truth_relevant_ids
            )
            result.precision_at_k = ir_metrics["precision_at_k"]
            result.recall_at_k = ir_metrics["recall_at_k"]
            result.map_score = ir_metrics["map_score"]
        
        # Search-specific evaluations
        if 'diversity' in request.evaluation_metrics:
            result.result_diversity = search_evaluator.evaluate_result_diversity(request.search_results)
        
        # Cross-modal accuracy (if applicable)
        if request.search_type in ['cross_modal', 'multimodal']:
            result.cross_modal_accuracy = evaluate_cross_modal_search_accuracy(request.search_results)
        
        # Ranking quality
        result.ranking_quality = evaluate_ranking_quality(request.search_results)
        
        # Generate per-result scores
        result.per_result_scores = generate_per_result_scores(request.search_results)
        
        # Generate optimization suggestions
        result.optimization_suggestions = generate_search_optimization_suggestions(result)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search evaluation failed: {str(e)}")

@app.post("/evaluate/batch")
async def batch_evaluate(evaluation_requests: List[Dict[str, Any]]):
    """Batch evaluation for multiple requests"""
    results = []
    
    for i, request_data in enumerate(evaluation_requests):
        try:
            eval_type = request_data.get("type", "multimodal")
            
            if eval_type == "multimodal":
                request = MultimodalEvaluationRequest(**request_data["data"])
                result = await evaluate_multimodal_response(request)
            elif eval_type == "document_processing":
                request = DocumentProcessingEvaluationRequest(**request_data["data"])
                result = await evaluate_document_processing(request)
            elif eval_type == "search":
                request = SearchEvaluationRequest(**request_data["data"])
                result = await evaluate_search_quality(request)
            else:
                result = {"error": f"Unknown evaluation type: {eval_type}"}
            
            results.append({"index": i, "result": result})
            
        except Exception as e:
            results.append({"index": i, "error": str(e)})
    
    return {"batch_results": results}

# Helper functions
def generate_multimodal_recommendations(result: MultimodalEvaluationResult) -> List[str]:
    """Generate recommendations based on evaluation results"""
    recommendations = []
    
    if result.image_relevance < 0.7:
        recommendations.append("Consider improving image relevance by using more targeted visual content")
    
    if result.cross_modal_consistency < 0.6:
        recommendations.append("Improve text-image alignment and relationship identification")
    
    if result.visual_grounding < 0.5:
        recommendations.append("Increase references to visual content in generated answers")
    
    if result.ragas_metrics.get("basic_relevance", 0) < 0.7:
        recommendations.append("Enhance text-based relevance through better keyword matching")
    
    return recommendations

def generate_processing_suggestions(result: DocumentProcessingEvaluationResult) -> List[str]:
    """Generate processing improvement suggestions"""
    suggestions = []
    
    if result.extraction_completeness < 0.8:
        suggestions.append("Consider adjusting extraction parameters or trying alternative processing methods")
    
    if result.chunking_quality < 0.7:
        suggestions.append("Review chunking strategy and adjust chunk size/overlap parameters")
    
    if result.relationship_accuracy < 0.6:
        suggestions.append("Improve relationship detection algorithms or add manual validation")
    
    if result.metadata_completeness < 0.5:
        suggestions.append("Enhance metadata extraction or consider additional preprocessing")
    
    return suggestions

def generate_search_optimization_suggestions(result: SearchEvaluationResult) -> List[str]:
    """Generate search optimization suggestions"""
    suggestions = []
    
    if result.map_score < 0.6:
        suggestions.append("Consider adjusting search algorithm weights or ranking functions")
    
    if result.result_diversity < 0.5:
        suggestions.append("Implement result diversification techniques like MMR")
    
    if result.cross_modal_accuracy < 0.7:
        suggestions.append("Improve cross-modal embedding alignment and similarity thresholds")
    
    return suggestions

def evaluate_cross_modal_search_accuracy(search_results: List[Dict[str, Any]]) -> float:
    """Evaluate accuracy of cross-modal search results"""
    if not search_results:
        return 0.0
    
    # Simple heuristic based on content type diversity and confidence scores
    content_types = [result.get("metadata", {}).get("content_type", "text") for result in search_results]
    type_diversity = len(set(content_types)) / len(content_types)
    
    confidence_scores = [result.get("score", 0.5) for result in search_results]
    avg_confidence = np.mean(confidence_scores)
    
    return (type_diversity + avg_confidence) / 2

def evaluate_ranking_quality(search_results: List[Dict[str, Any]]) -> float:
    """Evaluate quality of result ranking"""
    if not search_results:
        return 0.0
    
    scores = [result.get("score", 0.5) for result in search_results]
    
    # Check if scores are in descending order
    is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    sorting_score = 1.0 if is_sorted else 0.5
    
    # Check score distribution
    if len(scores) > 1:
        score_variance = np.var(scores)
        variance_score = min(score_variance * 2, 1.0)  # Higher variance = better discrimination
    else:
        variance_score = 0.5
    
    return (sorting_score + variance_score) / 2

def generate_per_result_scores(search_results: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """Generate individual scores for each search result"""
    per_result_scores = []
    
    for i, result in enumerate(search_results):
        score_dict = {
            "rank": i + 1,
            "relevance_score": result.get("score", 0.5),
            "confidence": result.get("metadata", {}).get("confidence", 0.5)
        }
        per_result_scores.append(score_dict)
    
    return per_result_scores

if __name__ == "__main__":
    print("🚀 Starting Multimodal RAGAS Evaluation Service")
    print(f"📍 Service will be available at: http://localhost:{SERVICE_PORT}")
    print(f"📊 Health check: http://localhost:{SERVICE_PORT}/health")
    print(f"📖 API docs: http://localhost:{SERVICE_PORT}/docs")
    
    # Start server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info",
        workers=1
    )