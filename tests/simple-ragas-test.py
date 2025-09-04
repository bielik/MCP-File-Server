#!/usr/bin/env python3
"""
Simple RAGAS Testing
Test RAGAS evaluation functionality with basic metrics
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add user site packages to path for Windows
user_site_packages = Path.home() / "AppData" / "Roaming" / "Python" / "Python312" / "site-packages"
if user_site_packages.exists() and str(user_site_packages) not in sys.path:
    sys.path.insert(0, str(user_site_packages))

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

class SimpleRAGASEvaluator:
    """Simple RAGAS-style evaluation without external dependencies"""
    
    @staticmethod
    def calculate_basic_relevance(query: str, contexts: List[str]) -> float:
        """Calculate basic relevance score using keyword overlap"""
        if not query or not contexts:
            return 0.0
            
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
    
    @staticmethod
    def calculate_faithfulness(contexts: List[str], answer: str) -> float:
        """Calculate faithfulness of answer to contexts"""
        if not contexts or not answer:
            return 0.0
        
        # Simple faithfulness: check if answer content is supported by contexts
        answer_words = set(answer.lower().split())
        context_content = " ".join(contexts).lower()
        context_words = set(context_content.split())
        
        if not context_words:
            return 0.0
        
        # Calculate how much of the answer is grounded in contexts
        grounded_words = answer_words.intersection(context_words)
        faithfulness = len(grounded_words) / len(answer_words) if answer_words else 0.0
        
        return min(faithfulness, 1.0)
    
    def evaluate_rag_response(self, query: str, contexts: List[str], answer: str, 
                            ground_truth: str = None) -> Dict[str, float]:
        """Evaluate a complete RAG response"""
        metrics = {}
        
        # Core RAGAS-style metrics
        metrics["basic_relevance"] = self.calculate_basic_relevance(query, contexts)
        metrics["context_utilization"] = self.calculate_context_utilization(contexts, answer)
        metrics["answer_completeness"] = self.calculate_answer_completeness(query, answer)
        metrics["faithfulness"] = self.calculate_faithfulness(contexts, answer)
        
        # Additional quality metrics
        if ground_truth:
            metrics["answer_similarity"] = self.calculate_answer_similarity(answer, ground_truth)
        
        # Calculate overall score
        core_metrics = [metrics["basic_relevance"], metrics["context_utilization"], 
                       metrics["answer_completeness"], metrics["faithfulness"]]
        metrics["overall_score"] = sum(core_metrics) / len(core_metrics)
        
        return metrics
    
    @staticmethod
    def calculate_answer_similarity(answer: str, ground_truth: str) -> float:
        """Calculate similarity between answer and ground truth"""
        if not answer or not ground_truth:
            return 0.0
        
        answer_words = set(answer.lower().split())
        truth_words = set(ground_truth.lower().split())
        
        if not answer_words or not truth_words:
            return 0.0
        
        # Jaccard similarity
        intersection = len(answer_words.intersection(truth_words))
        union = len(answer_words.union(truth_words))
        
        return intersection / union if union > 0 else 0.0

def run_ragas_tests():
    """Run comprehensive RAGAS evaluation tests"""
    print("RAGAS EVALUATION TESTING SUITE")
    print("=" * 80)
    
    evaluator = SimpleRAGASEvaluator()
    test_results = []
    
    # Test case 1: High-quality RAG response
    print("\n[TEST 1] High-Quality RAG Response")
    query1 = "What are the benefits of machine learning in healthcare?"
    contexts1 = [
        "Machine learning in healthcare can improve diagnostic accuracy by analyzing medical images and patient data.",
        "Healthcare ML systems can predict patient outcomes and help with early intervention strategies.",
        "Automated analysis of medical records using ML can reduce human error and increase efficiency."
    ]
    answer1 = ("Machine learning offers significant benefits in healthcare including improved diagnostic accuracy "
              "through medical image analysis, better patient outcome prediction for early intervention, and "
              "reduced human error through automated analysis of medical records.")
    ground_truth1 = ("ML in healthcare improves diagnoses, predicts outcomes, and reduces errors through automation.")
    
    start_time = time.time()
    metrics1 = evaluator.evaluate_rag_response(query1, contexts1, answer1, ground_truth1)
    duration1 = (time.time() - start_time) * 1000
    
    print(f"   Basic Relevance: {metrics1['basic_relevance']:.3f}")
    print(f"   Context Utilization: {metrics1['context_utilization']:.3f}")
    print(f"   Answer Completeness: {metrics1['answer_completeness']:.3f}")
    print(f"   Faithfulness: {metrics1['faithfulness']:.3f}")
    print(f"   Answer Similarity: {metrics1['answer_similarity']:.3f}")
    print(f"   Overall Score: {metrics1['overall_score']:.3f}")
    print(f"   Evaluation Time: {duration1:.1f}ms")
    
    test_results.append({
        "test_name": "High-Quality RAG Response",
        "metrics": metrics1,
        "duration_ms": duration1,
        "quality_gate": "PASS" if metrics1['overall_score'] >= 0.7 else "FAIL"
    })
    
    # Test case 2: Poor-quality RAG response
    print("\n[TEST 2] Poor-Quality RAG Response")
    query2 = "How does artificial intelligence work?"
    contexts2 = [
        "Artificial intelligence uses algorithms and data to make predictions and decisions.",
        "Machine learning is a subset of AI that learns from data patterns.",
        "Deep learning uses neural networks to process complex information."
    ]
    answer2 = "Cooking pasta requires boiling water and adding salt for flavor."
    ground_truth2 = "AI works by processing data through algorithms to make intelligent decisions."
    
    start_time = time.time()
    metrics2 = evaluator.evaluate_rag_response(query2, contexts2, answer2, ground_truth2)
    duration2 = (time.time() - start_time) * 1000
    
    print(f"   Basic Relevance: {metrics2['basic_relevance']:.3f}")
    print(f"   Context Utilization: {metrics2['context_utilization']:.3f}")
    print(f"   Answer Completeness: {metrics2['answer_completeness']:.3f}")
    print(f"   Faithfulness: {metrics2['faithfulness']:.3f}")
    print(f"   Answer Similarity: {metrics2['answer_similarity']:.3f}")
    print(f"   Overall Score: {metrics2['overall_score']:.3f}")
    print(f"   Evaluation Time: {duration2:.1f}ms")
    
    test_results.append({
        "test_name": "Poor-Quality RAG Response",
        "metrics": metrics2,
        "duration_ms": duration2,
        "quality_gate": "PASS" if metrics2['overall_score'] < 0.3 else "FAIL"  # Expect low score
    })
    
    # Test case 3: Partial-quality RAG response
    print("\n[TEST 3] Partial-Quality RAG Response")
    query3 = "What are the applications of deep learning?"
    contexts3 = [
        "Deep learning is used in computer vision for image recognition and object detection.",
        "Natural language processing benefits from deep learning through improved text understanding.",
        "Deep learning enables autonomous vehicles to process sensor data and make driving decisions."
    ]
    answer3 = ("Deep learning has applications in computer vision and natural language processing. "
              "It can also be used for recommendation systems.")
    ground_truth3 = ("Deep learning applications include computer vision, NLP, autonomous vehicles, and many other domains.")
    
    start_time = time.time()
    metrics3 = evaluator.evaluate_rag_response(query3, contexts3, answer3, ground_truth3)
    duration3 = (time.time() - start_time) * 1000
    
    print(f"   Basic Relevance: {metrics3['basic_relevance']:.3f}")
    print(f"   Context Utilization: {metrics3['context_utilization']:.3f}")
    print(f"   Answer Completeness: {metrics3['answer_completeness']:.3f}")
    print(f"   Faithfulness: {metrics3['faithfulness']:.3f}")
    print(f"   Answer Similarity: {metrics3['answer_similarity']:.3f}")
    print(f"   Overall Score: {metrics3['overall_score']:.3f}")
    print(f"   Evaluation Time: {duration3:.1f}ms")
    
    test_results.append({
        "test_name": "Partial-Quality RAG Response",
        "metrics": metrics3,
        "duration_ms": duration3,
        "quality_gate": "PASS" if 0.4 <= metrics3['overall_score'] <= 0.8 else "FAIL"  # Expect medium score
    })
    
    # Test case 4: Multimodal content simulation
    print("\n[TEST 4] Multimodal Content Evaluation")
    query4 = "Explain the neural network architecture shown in the diagram"
    contexts4 = [
        "The diagram shows a three-layer neural network with input, hidden, and output layers.",
        "Each neuron in the hidden layer receives weighted inputs from all input neurons.",
        "The output layer uses activation functions to produce final predictions."
    ]
    answer4 = ("The neural network diagram illustrates a three-layer architecture consisting of input neurons, "
              "a hidden layer with weighted connections, and an output layer that applies activation functions "
              "to generate final predictions.")
    ground_truth4 = ("The diagram shows a standard feedforward neural network with three layers and weighted connections.")
    
    start_time = time.time()
    metrics4 = evaluator.evaluate_rag_response(query4, contexts4, answer4, ground_truth4)
    duration4 = (time.time() - start_time) * 1000
    
    # Add multimodal-specific metrics
    visual_grounding = 0.9  # Simulated - answer references the diagram
    cross_modal_consistency = 0.85  # Simulated - text and visual content align
    
    print(f"   Basic Relevance: {metrics4['basic_relevance']:.3f}")
    print(f"   Context Utilization: {metrics4['context_utilization']:.3f}")
    print(f"   Answer Completeness: {metrics4['answer_completeness']:.3f}")
    print(f"   Faithfulness: {metrics4['faithfulness']:.3f}")
    print(f"   Visual Grounding: {visual_grounding:.3f}")
    print(f"   Cross-Modal Consistency: {cross_modal_consistency:.3f}")
    print(f"   Overall Score: {metrics4['overall_score']:.3f}")
    print(f"   Evaluation Time: {duration4:.1f}ms")
    
    metrics4["visual_grounding"] = visual_grounding
    metrics4["cross_modal_consistency"] = cross_modal_consistency
    
    test_results.append({
        "test_name": "Multimodal Content Evaluation",
        "metrics": metrics4,
        "duration_ms": duration4,
        "quality_gate": "PASS" if metrics4['overall_score'] >= 0.7 else "FAIL"
    })
    
    # Test performance with batch evaluation
    print("\n[TEST 5] Batch Evaluation Performance")
    batch_queries = [
        ("What is machine learning?", ["ML is a type of AI", "It learns from data"], "ML is AI that learns from data"),
        ("How do neural networks work?", ["Networks have layers", "They use weights"], "Networks use layers and weights"),
        ("What is deep learning?", ["Deep learning uses many layers", "It processes complex patterns"], "Deep learning uses many layers for complex patterns")
    ]
    
    start_time = time.time()
    batch_results = []
    
    for query, contexts, answer in batch_queries:
        metrics = evaluator.evaluate_rag_response(query, contexts, answer)
        batch_results.append(metrics)
    
    batch_duration = (time.time() - start_time) * 1000
    avg_score = sum(r["overall_score"] for r in batch_results) / len(batch_results)
    
    print(f"   Batch Size: {len(batch_queries)}")
    print(f"   Average Score: {avg_score:.3f}")
    print(f"   Total Time: {batch_duration:.1f}ms")
    print(f"   Avg Time per Query: {batch_duration/len(batch_queries):.1f}ms")
    
    test_results.append({
        "test_name": "Batch Evaluation Performance",
        "metrics": {"average_score": avg_score, "batch_size": len(batch_queries)},
        "duration_ms": batch_duration,
        "quality_gate": "PASS" if batch_duration/len(batch_queries) < 100 else "FAIL"  # < 100ms per query
    })
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("RAGAS EVALUATION TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(test_results)
    passed_tests = len([r for r in test_results if r["quality_gate"] == "PASS"])
    
    for result in test_results:
        gate_icon = "[PASS]" if result["quality_gate"] == "PASS" else "[FAIL]"
        print(f"{gate_icon} {result['test_name']} ({result['duration_ms']:.1f}ms)")
        
        if "overall_score" in result["metrics"]:
            print(f"        Overall Score: {result['metrics']['overall_score']:.3f}")
    
    print(f"\nOVERALL RESULTS:")
    print(f"   Tests Passed: {passed_tests}/{total_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Quality gate assessment
    if passed_tests == total_tests:
        print("\n[SUCCESS] All RAGAS evaluation tests passed!")
        print("Phase 2 RAG evaluation system is functioning correctly.")
    else:
        print(f"\n[ATTENTION] {total_tests - passed_tests} tests failed.")
        print("Review evaluation logic and quality thresholds.")
    
    # Save detailed report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests/total_tests)*100
        },
        "test_results": test_results,
        "dependencies": {
            "requests_available": REQUESTS_AVAILABLE,
            "pandas_available": PANDAS_AVAILABLE
        }
    }
    
    report_file = Path(__file__).parent / f"ragas_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_ragas_tests()
    exit_code = 0 if success else 1
    print(f"\nExiting with code: {exit_code}")
    sys.exit(exit_code)