#!/usr/bin/env python3
"""
Service Diagnosis and Repair Script
Diagnoses and fixes critical issues with multimodal RAG services
"""

import os
import sys
import json
import subprocess
import requests
import time
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServiceDiagnostic:
    def __init__(self):
        self.services = {
            'clip': 'http://127.0.0.1:8002',
            'mclip': 'http://127.0.0.1:8003', 
            'docling': 'http://127.0.0.1:8004',
            'qdrant': 'http://127.0.0.1:6333',
            'ragas': 'http://127.0.0.1:8001'
        }
        
        self.diagnosis_results = {}
        
    def check_pytorch_cuda(self):
        """Check PyTorch and CUDA setup"""
        logger.info("Checking PyTorch and CUDA setup...")
        
        try:
            import torch
            import transformers
            
            result = {
                'pytorch_version': torch.__version__,
                'transformers_version': transformers.__version__,
                'cuda_available': torch.cuda.is_available(),
                'cuda_version': torch.version.cuda if torch.cuda.is_available() else None,
                'gpu_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
                'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                'current_device': str(torch.cuda.current_device()) if torch.cuda.is_available() else 'cpu'
            }
            
            logger.info(f"PyTorch: {result['pytorch_version']}")
            logger.info(f"Transformers: {result['transformers_version']}")
            logger.info(f"CUDA Available: {result['cuda_available']}")
            if result['cuda_available']:
                logger.info(f"GPU: {result['gpu_name']}")
            
            return result
            
        except ImportError as e:
            logger.error(f"PyTorch/Transformers import failed: {e}")
            return {'error': str(e)}

    def test_clip_model_loading(self):
        """Test CLIP model loading directly"""
        logger.info("Testing CLIP model loading...")
        
        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
            
            # Test loading the exact model used in service
            model_name = "openai/clip-vit-base-patch32"
            logger.info(f"Loading {model_name}...")
            
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info(f"Using device: {device}")
            
            # Try loading each component
            model = CLIPModel.from_pretrained(model_name, trust_remote_code=True)
            processor = CLIPProcessor.from_pretrained(model_name, trust_remote_code=True) 
            tokenizer = CLIPTokenizer.from_pretrained(model_name, trust_remote_code=True)
            
            # Move to GPU if available
            model = model.to(device)
            
            # Test a simple inference
            test_text = ["a photo of a cat"]
            inputs = tokenizer(test_text, return_tensors="pt", padding=True)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            with torch.no_grad():
                text_features = model.get_text_features(**inputs)
            
            logger.info(f"✓ CLIP model loaded successfully")
            logger.info(f"✓ Text embedding shape: {text_features.shape}")
            logger.info(f"✓ Device: {text_features.device}")
            
            return {
                'status': 'SUCCESS',
                'model_name': model_name,
                'device': str(device),
                'embedding_dim': text_features.shape[1],
                'text_features_shape': list(text_features.shape)
            }
            
        except Exception as e:
            logger.error(f"✗ CLIP model loading failed: {e}")
            return {
                'status': 'FAILED', 
                'error': str(e),
                'traceback': str(e.__class__.__name__)
            }

    def start_ragas_service(self):
        """Start RAGAS evaluation service"""
        logger.info("Starting RAGAS evaluation service...")
        
        ragas_script = Path("tests/rag-evaluation/python/evaluation_service.py")
        if not ragas_script.exists():
            logger.error(f"RAGAS script not found: {ragas_script}")
            return {'status': 'FAILED', 'error': 'Script not found'}
        
        try:
            # Check if already running
            try:
                response = requests.get(f"{self.services['ragas']}/health", timeout=2)
                if response.status_code == 200:
                    logger.info("✓ RAGAS service already running")
                    return {'status': 'ALREADY_RUNNING'}
            except:
                pass  # Not running, start it
            
            # Start the service in background
            python_env = Path("tests/rag-evaluation/python-env/Scripts/python.exe")
            if not python_env.exists():
                logger.error("Python environment not found")
                return {'status': 'FAILED', 'error': 'Python env not found'}
            
            cmd = [str(python_env), str(ragas_script)]
            logger.info(f"Starting RAGAS service: {' '.join(cmd)}")
            
            # Start process in background
            process = subprocess.Popen(
                cmd, 
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Wait a bit and check if it started
            time.sleep(3)
            
            try:
                response = requests.get(f"{self.services['ragas']}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("✓ RAGAS service started successfully")
                    return {'status': 'STARTED', 'pid': process.pid}
                else:
                    logger.warning(f"RAGAS service not responding correctly: HTTP {response.status_code}")
                    return {'status': 'STARTED_NO_RESPONSE', 'pid': process.pid}
            except Exception as e:
                logger.warning(f"RAGAS service may be starting: {e}")
                return {'status': 'STARTING', 'pid': process.pid}
                
        except Exception as e:
            logger.error(f"Failed to start RAGAS service: {e}")
            return {'status': 'FAILED', 'error': str(e)}

    def diagnose_service_issues(self):
        """Run comprehensive service diagnosis"""
        logger.info("Running comprehensive service diagnosis...")
        
        # 1. Check PyTorch/CUDA setup
        self.diagnosis_results['pytorch_cuda'] = self.check_pytorch_cuda()
        
        # 2. Test CLIP model loading
        self.diagnosis_results['clip_model_loading'] = self.test_clip_model_loading()
        
        # 3. Check service health
        self.diagnosis_results['service_health'] = {}
        for service, url in self.services.items():
            try:
                response = requests.get(f"{url}/health", timeout=3)
                self.diagnosis_results['service_health'][service] = {
                    'status': 'HEALTHY' if response.status_code == 200 else 'UNHEALTHY',
                    'status_code': response.status_code,
                    'response': response.json() if response.status_code == 200 else response.text[:200]
                }
            except Exception as e:
                self.diagnosis_results['service_health'][service] = {
                    'status': 'UNAVAILABLE',
                    'error': str(e)
                }
        
        # 4. Try to start RAGAS if not running
        if self.diagnosis_results['service_health'].get('ragas', {}).get('status') != 'HEALTHY':
            self.diagnosis_results['ragas_startup'] = self.start_ragas_service()
        
        return self.diagnosis_results

    def create_repair_recommendations(self):
        """Create specific repair recommendations"""
        recommendations = []
        
        results = self.diagnosis_results
        
        # PyTorch/CUDA issues
        pytorch = results.get('pytorch_cuda', {})
        if 'error' in pytorch:
            recommendations.append({
                'priority': 'CRITICAL',
                'issue': 'PyTorch/Transformers not available',
                'action': 'Install PyTorch and transformers in the Python environment',
                'command': 'pip install torch transformers'
            })
        elif not pytorch.get('cuda_available', False):
            recommendations.append({
                'priority': 'HIGH', 
                'issue': 'CUDA not available',
                'action': 'Install PyTorch with CUDA support',
                'command': 'pip install torch --index-url https://download.pytorch.org/whl/cu121'
            })
        
        # CLIP model loading issues
        clip_loading = results.get('clip_model_loading', {})
        if clip_loading.get('status') == 'FAILED':
            recommendations.append({
                'priority': 'CRITICAL',
                'issue': 'CLIP model loading failed',
                'action': 'Debug model loading in CLIP service',
                'details': clip_loading.get('error', 'Unknown error')
            })
        
        # Service health issues
        service_health = results.get('service_health', {})
        for service, health in service_health.items():
            if health.get('status') != 'HEALTHY':
                recommendations.append({
                    'priority': 'HIGH' if service in ['clip', 'qdrant'] else 'MEDIUM',
                    'issue': f'{service} service not healthy',
                    'status': health.get('status'),
                    'action': f'Restart {service} service and check logs'
                })
        
        # RAGAS service
        if results.get('ragas_startup', {}).get('status') not in ['ALREADY_RUNNING', 'STARTED']:
            recommendations.append({
                'priority': 'MEDIUM',
                'issue': 'RAGAS evaluation service not running',
                'action': 'Manually start RAGAS service for quality assessment'
            })
        
        return recommendations

    def generate_report(self):
        """Generate comprehensive diagnosis report"""
        logger.info("Generating diagnosis report...")
        
        # Run diagnosis
        self.diagnose_service_issues()
        
        # Generate recommendations
        recommendations = self.create_repair_recommendations()
        
        # Create report
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'diagnosis_results': self.diagnosis_results,
            'recommendations': recommendations,
            'summary': {
                'critical_issues': len([r for r in recommendations if r.get('priority') == 'CRITICAL']),
                'high_priority': len([r for r in recommendations if r.get('priority') == 'HIGH']),
                'medium_priority': len([r for r in recommendations if r.get('priority') == 'MEDIUM']),
                'services_healthy': len([s for s in self.diagnosis_results.get('service_health', {}).values() if s.get('status') == 'HEALTHY']),
                'services_total': len(self.services)
            }
        }
        
        return report

def main():
    """Main execution"""
    print("=" * 80)
    print("MULTIMODAL RAG SERVICES - DIAGNOSIS AND REPAIR")
    print("=" * 80)
    
    diagnostic = ServiceDiagnostic()
    report = diagnostic.generate_report()
    
    # Print summary
    print(f"\nDiagnosis completed at: {report['timestamp']}")
    print(f"Services healthy: {report['summary']['services_healthy']}/{report['summary']['services_total']}")
    print(f"Issues found: {report['summary']['critical_issues']} critical, {report['summary']['high_priority']} high, {report['summary']['medium_priority']} medium")
    
    # Print recommendations
    if report['recommendations']:
        print("\nREPAIR RECOMMENDATIONS:")
        print("-" * 50)
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. [{rec['priority']}] {rec['issue']}")
            print(f"   Action: {rec['action']}")
            if 'command' in rec:
                print(f"   Command: {rec['command']}")
            if 'details' in rec:
                print(f"   Details: {rec['details']}")
            print()
    
    # Save detailed report
    output_file = f"tests/service_diagnosis_report_{int(time.time())}.json"
    try:
        os.makedirs('tests', exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Detailed report saved to: {output_file}")
    except Exception as e:
        print(f"Could not save report: {e}")
    
    # Return exit code based on critical issues
    return 1 if report['summary']['critical_issues'] > 0 else 0

if __name__ == "__main__":
    sys.exit(main())