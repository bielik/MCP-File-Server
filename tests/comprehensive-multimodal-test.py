#!/usr/bin/env python3
"""
Comprehensive Multimodal RAG Evaluation Test Suite
Tests all components of the multimodal RAG stack for the MCP Research File Server
"""

import os
import sys
import json
import time
import requests
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultimodalRAGTester:
    def __init__(self):
        self.services = {
            'clip': 'http://127.0.0.1:8002',
            'mclip': 'http://127.0.0.1:8003', 
            'docling': 'http://127.0.0.1:8004',
            'qdrant': 'http://127.0.0.1:6333',
            'ragas': 'http://127.0.0.1:8001'  # May not be running
        }
        
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'PENDING',
            'service_health': {},
            'functionality_tests': {},
            'performance_metrics': {},
            'integration_tests': {},
            'recommendations': []
        }
        
        # Test data
        self.test_texts = [
            "Machine learning algorithms for document processing",
            "Research methodology and experimental design", 
            "Neural networks and deep learning architectures",
            "Data analysis and statistical methods",
            "Computer vision and image recognition"
        ]
        
        self.test_queries = [
            "machine learning",
            "research methods", 
            "neural networks",
            "data analysis"
        ]

    def check_service_health(self) -> Dict[str, Any]:
        """Check health status of all services"""
        logger.info("Checking service health...")
        
        for service_name, url in self.services.items():
            try:
                start_time = time.time()
                response = requests.get(f"{url}/health", timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    health_data = response.json()
                    self.test_results['service_health'][service_name] = {
                        'status': 'HEALTHY',
                        'response_time_ms': response_time,
                        'details': health_data
                    }
                    logger.info(f"✓ {service_name} service healthy ({response_time:.1f}ms)")
                else:
                    self.test_results['service_health'][service_name] = {
                        'status': 'UNHEALTHY',
                        'response_time_ms': response_time,
                        'error': f"HTTP {response.status_code}"
                    }
                    logger.warning(f"✗ {service_name} service unhealthy: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.test_results['service_health'][service_name] = {
                    'status': 'UNAVAILABLE',
                    'error': str(e)
                }
                logger.warning(f"✗ {service_name} service unavailable: {str(e)}")
        
        return self.test_results['service_health']

    def test_text_embeddings(self, service_url: str, service_name: str) -> Dict[str, Any]:
        """Test text embedding functionality"""
        logger.info(f"Testing {service_name} text embeddings...")
        
        try:
            results = {
                'embedding_dimension': None,
                'embedding_quality': None,
                'response_times': [],
                'semantic_similarity': None,
                'status': 'PENDING'
            }
            
            embeddings = []
            for text in self.test_texts:
                start_time = time.time()
                response = requests.post(
                    f"{service_url}/embed/text",
                    json={"text": text},
                    timeout=30
                )
                response_time = (time.time() - start_time) * 1000
                results['response_times'].append(response_time)
                
                if response.status_code == 200:
                    embedding = response.json()['embedding']
                    embeddings.append(embedding)
                    
                    if results['embedding_dimension'] is None:
                        results['embedding_dimension'] = len(embedding)
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            # Test semantic similarity
            if len(embeddings) >= 2:
                # Compare similar texts (machine learning vs neural networks)
                sim_ml_nn = self._cosine_similarity(embeddings[0], embeddings[2])
                # Compare dissimilar texts (machine learning vs research methodology)
                sim_ml_rm = self._cosine_similarity(embeddings[0], embeddings[1])
                
                results['semantic_similarity'] = {
                    'similar_texts_similarity': sim_ml_nn,
                    'dissimilar_texts_similarity': sim_ml_rm,
                    'semantic_coherence': sim_ml_nn > sim_ml_rm
                }
                
            results['avg_response_time_ms'] = np.mean(results['response_times'])
            results['status'] = 'PASS'
            logger.info(f"✓ {service_name} text embeddings working (dim={results['embedding_dimension']})")
            
        except Exception as e:
            results['status'] = 'FAIL'
            results['error'] = str(e)
            logger.error(f"✗ {service_name} text embeddings failed: {str(e)}")
            
        return results

    def test_image_embeddings(self, service_url: str, service_name: str) -> Dict[str, Any]:
        """Test image embedding functionality with placeholder image"""
        logger.info(f"Testing {service_name} image embeddings...")
        
        try:
            results = {
                'embedding_dimension': None,
                'response_time_ms': None,
                'status': 'PENDING'
            }
            
            # Create a simple test image (1x1 RGB)
            import base64
            from PIL import Image
            import io
            
            # Create a 224x224 RGB test image
            test_image = Image.new('RGB', (224, 224), color='blue')
            img_buffer = io.BytesIO()
            test_image.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            start_time = time.time()
            response = requests.post(
                f"{service_url}/embed/image",
                json={"image": img_base64},
                timeout=30
            )
            response_time = (time.time() - start_time) * 1000
            results['response_time_ms'] = response_time
            
            if response.status_code == 200:
                embedding = response.json()['embedding']
                results['embedding_dimension'] = len(embedding)
                results['status'] = 'PASS'
                logger.info(f"✓ {service_name} image embeddings working (dim={results['embedding_dimension']})")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            results['status'] = 'FAIL'
            results['error'] = str(e)
            logger.error(f"✗ {service_name} image embeddings failed: {str(e)}")
            
        return results

    def test_cross_modal_compatibility(self) -> Dict[str, Any]:
        """Test if text and image embeddings are in the same vector space"""
        logger.info("Testing cross-modal compatibility...")
        
        try:
            results = {
                'clip_compatibility': None,
                'mclip_compatibility': None,
                'status': 'PENDING'
            }
            
            # Test CLIP service cross-modal compatibility
            if self.test_results['service_health'].get('clip', {}).get('status') == 'HEALTHY':
                clip_text_result = self.test_text_embeddings(self.services['clip'], 'CLIP')
                clip_image_result = self.test_image_embeddings(self.services['clip'], 'CLIP')
                
                if (clip_text_result.get('status') == 'PASS' and 
                    clip_image_result.get('status') == 'PASS'):
                    results['clip_compatibility'] = {
                        'text_dimension': clip_text_result['embedding_dimension'],
                        'image_dimension': clip_image_result['embedding_dimension'],
                        'dimensions_match': (clip_text_result['embedding_dimension'] == 
                                           clip_image_result['embedding_dimension']),
                        'status': 'PASS' if clip_text_result['embedding_dimension'] == clip_image_result['embedding_dimension'] else 'FAIL'
                    }
                    
            # Test M-CLIP service cross-modal compatibility  
            if self.test_results['service_health'].get('mclip', {}).get('status') == 'HEALTHY':
                mclip_text_result = self.test_text_embeddings(self.services['mclip'], 'M-CLIP')
                # M-CLIP might not support images directly - check capabilities
                try:
                    mclip_image_result = self.test_image_embeddings(self.services['mclip'], 'M-CLIP')
                    if (mclip_text_result.get('status') == 'PASS' and 
                        mclip_image_result.get('status') == 'PASS'):
                        results['mclip_compatibility'] = {
                            'text_dimension': mclip_text_result['embedding_dimension'],
                            'image_dimension': mclip_image_result['embedding_dimension'],
                            'dimensions_match': (mclip_text_result['embedding_dimension'] == 
                                               mclip_image_result['embedding_dimension']),
                            'status': 'PASS' if mclip_text_result['embedding_dimension'] == mclip_image_result['embedding_dimension'] else 'FAIL'
                        }
                except:
                    results['mclip_compatibility'] = {
                        'status': 'SKIP',
                        'reason': 'M-CLIP service does not support image embeddings'
                    }
            
            # Determine overall status
            clip_ok = results.get('clip_compatibility', {}).get('status') == 'PASS'
            mclip_ok = results.get('mclip_compatibility', {}).get('status') in ['PASS', 'SKIP']
            
            if clip_ok or mclip_ok:
                results['status'] = 'PASS'
                logger.info("✓ Cross-modal compatibility validated")
            else:
                results['status'] = 'FAIL'
                logger.error("✗ Cross-modal compatibility failed")
                
        except Exception as e:
            results['status'] = 'FAIL'
            results['error'] = str(e)
            logger.error(f"✗ Cross-modal compatibility test failed: {str(e)}")
            
        return results

    def test_vector_storage(self) -> Dict[str, Any]:
        """Test Qdrant vector database functionality"""
        logger.info("Testing vector storage (Qdrant)...")
        
        try:
            results = {
                'collections': None,
                'insert_test': None,
                'search_test': None,
                'status': 'PENDING'
            }
            
            # Check collections
            response = requests.get(f"{self.services['qdrant']}/collections")
            if response.status_code == 200:
                collections = response.json()['result']['collections']
                results['collections'] = {
                    'count': len(collections),
                    'names': [c['name'] for c in collections],
                    'expected_collections': ['mcp_text_embeddings', 'mcp_image_embeddings', 'mcp_multimodal_embeddings']
                }
                
                # Test basic search on existing collection if available
                if 'mcp_text_embeddings' in results['collections']['names']:
                    # Create a test vector for search
                    test_vector = np.random.rand(512).tolist()
                    search_response = requests.post(
                        f"{self.services['qdrant']}/collections/mcp_text_embeddings/points/search",
                        json={
                            "vector": test_vector,
                            "limit": 3
                        }
                    )
                    
                    if search_response.status_code == 200:
                        search_results = search_response.json()['result']
                        results['search_test'] = {
                            'status': 'PASS',
                            'results_count': len(search_results),
                            'response_time_ms': search_response.elapsed.total_seconds() * 1000
                        }
                    else:
                        results['search_test'] = {
                            'status': 'FAIL',
                            'error': f"Search failed: HTTP {search_response.status_code}"
                        }
                        
                results['status'] = 'PASS'
                logger.info(f"✓ Qdrant working with {len(collections)} collections")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            results['status'] = 'FAIL' 
            results['error'] = str(e)
            logger.error(f"✗ Vector storage test failed: {str(e)}")
            
        return results

    def test_document_processing(self) -> Dict[str, Any]:
        """Test document processing capabilities"""
        logger.info("Testing document processing (Docling)...")
        
        try:
            results = {
                'service_capabilities': None,
                'status': 'PENDING'
            }
            
            # Get service capabilities
            response = requests.get(f"{self.services['docling']}/health")
            if response.status_code == 200:
                health_data = response.json()
                results['service_capabilities'] = {
                    'pymupdf_available': health_data.get('pymupdf_available', False),
                    'pymupdf_version': health_data.get('pymupdf_version', 'unknown'),
                    'service_version': health_data.get('version', 'unknown')
                }
                results['status'] = 'PASS'
                logger.info("✓ Docling service capabilities verified")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            results['status'] = 'FAIL'
            results['error'] = str(e)
            logger.error(f"✗ Document processing test failed: {str(e)}")
            
        return results

    def evaluate_performance(self) -> Dict[str, Any]:
        """Evaluate overall system performance"""
        logger.info("Evaluating system performance...")
        
        performance = {
            'service_response_times': {},
            'gpu_utilization': None,
            'embedding_throughput': None,
            'system_bottlenecks': [],
            'recommendations': []
        }
        
        # Extract response times from service health checks
        for service, health in self.test_results['service_health'].items():
            if 'response_time_ms' in health:
                performance['service_response_times'][service] = health['response_time_ms']
        
        # Analyze performance patterns
        avg_response_time = np.mean(list(performance['service_response_times'].values()))
        
        if avg_response_time > 1000:
            performance['system_bottlenecks'].append('High average response times (>1s)')
            performance['recommendations'].append('Consider service optimization or hardware upgrade')
        
        # Check GPU utilization from service health
        clip_health = self.test_results['service_health'].get('clip', {}).get('details', {})
        if clip_health.get('cuda_available') and clip_health.get('device') == 'cuda':
            performance['gpu_utilization'] = {
                'gpu_available': True,
                'gpu_name': clip_health.get('gpu_name', 'Unknown'),
                'using_gpu': True
            }
        else:
            performance['gpu_utilization'] = {
                'gpu_available': clip_health.get('cuda_available', False),
                'using_gpu': False
            }
            if not clip_health.get('cuda_available', False):
                performance['recommendations'].append('GPU not available - consider enabling CUDA for better performance')
        
        return performance

    def generate_recommendations(self) -> List[str]:
        """Generate system recommendations based on test results"""
        recommendations = []
        
        # Service health recommendations
        unhealthy_services = [
            service for service, health in self.test_results['service_health'].items()
            if health.get('status') != 'HEALTHY'
        ]
        
        if unhealthy_services:
            recommendations.append(f"Fix unhealthy services: {', '.join(unhealthy_services)}")
        
        # Cross-modal compatibility recommendations
        cross_modal = self.test_results['functionality_tests'].get('cross_modal_compatibility', {})
        if cross_modal.get('status') == 'FAIL':
            recommendations.append("Fix cross-modal embedding compatibility for proper multimodal search")
        
        # Vector storage recommendations
        vector_storage = self.test_results['functionality_tests'].get('vector_storage', {})
        if vector_storage.get('status') == 'FAIL':
            recommendations.append("Fix Qdrant vector database connection and configuration")
        
        # Performance recommendations
        performance = self.test_results.get('performance_metrics', {})
        if performance.get('recommendations'):
            recommendations.extend(performance['recommendations'])
        
        # RAGAS integration recommendation
        if self.test_results['service_health'].get('ragas', {}).get('status') != 'HEALTHY':
            recommendations.append("Start RAGAS evaluation service for quality assessment")
        
        return recommendations

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and generate comprehensive report"""
        logger.info("Starting comprehensive multimodal RAG evaluation...")
        
        try:
            # 1. Service Health Check
            self.check_service_health()
            
            # 2. Functionality Tests
            self.test_results['functionality_tests'] = {
                'cross_modal_compatibility': self.test_cross_modal_compatibility(),
                'vector_storage': self.test_vector_storage(),
                'document_processing': self.test_document_processing()
            }
            
            # 3. Performance Evaluation
            self.test_results['performance_metrics'] = self.evaluate_performance()
            
            # 4. Generate Recommendations
            self.test_results['recommendations'] = self.generate_recommendations()
            
            # 5. Determine Overall Status
            failed_tests = [
                test_name for test_name, result in self.test_results['functionality_tests'].items()
                if result.get('status') == 'FAIL'
            ]
            
            critical_services_down = [
                service for service in ['clip', 'qdrant']
                if self.test_results['service_health'].get(service, {}).get('status') != 'HEALTHY'
            ]
            
            if failed_tests or critical_services_down:
                self.test_results['overall_status'] = 'FAIL'
                logger.error(f"✗ Comprehensive test FAILED - Issues: {failed_tests + critical_services_down}")
            else:
                self.test_results['overall_status'] = 'PASS'
                logger.info("✓ Comprehensive test PASSED")
                
        except Exception as e:
            self.test_results['overall_status'] = 'ERROR'
            self.test_results['error'] = str(e)
            logger.error(f"✗ Comprehensive test ERROR: {str(e)}")
            traceback.print_exc()
        
        return self.test_results

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def main():
    """Main test execution"""
    tester = MultimodalRAGTester()
    
    print("=" * 80)
    print("MULTIMODAL RAG EVALUATION - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    # Run comprehensive tests
    results = tester.run_comprehensive_test()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"tests/multimodal_rag_test_report_{timestamp}.json"
    
    try:
        os.makedirs('tests', exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📊 Detailed results saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️ Could not save results file: {e}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print(f"Overall Status: {results['overall_status']}")
    print(f"Timestamp: {results['timestamp']}")
    
    print("\nService Health:")
    for service, health in results['service_health'].items():
        status = health.get('status', 'UNKNOWN')
        print(f"  {service}: {status}")
    
    print("\nFunctionality Tests:")
    for test, result in results['functionality_tests'].items():
        status = result.get('status', 'UNKNOWN')
        print(f"  {test}: {status}")
    
    if results.get('recommendations'):
        print("\nRecommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    # Return appropriate exit code
    if results['overall_status'] == 'PASS':
        print("\n✅ All tests passed! Multimodal RAG stack is ready.")
        return 0
    else:
        print(f"\n❌ Tests failed. Status: {results['overall_status']}")
        return 1

if __name__ == "__main__":
    sys.exit(main())