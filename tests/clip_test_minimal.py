#!/usr/bin/env python3
"""
Minimal CLIP test to verify text embeddings work
Tests the CLIP text tower functionality that was requested by the user
"""

import requests
import json

def test_text_embeddings():
    """Test text embeddings with CLIP text tower"""
    print("[TEST] Testing CLIP text embeddings...")
    
    try:
        # Test text embedding endpoint
        response = requests.post('http://localhost:8004/embed/text', json={
            'texts': ['a photo of a cat', 'machine learning research', 'computer vision']
        })
        
        if response.status_code == 200:
            data = response.json()
            print("[PASS] Text embeddings generated successfully")
            print(f"   Embeddings shape: {len(data['embeddings'])} texts, {len(data['embeddings'][0])} dimensions")
            print(f"   Device: {data['device']}")
            print(f"   Model loaded: {data['model_loaded']}")
            print(f"   Model type: {data.get('model_type', 'unknown')}")
            
            # Validate embedding properties
            if len(data['embeddings']) == 3:
                print("[PASS] Correct number of embeddings generated")
            else:
                print(f"[FAIL] Expected 3 embeddings, got {len(data['embeddings'])}")
                
            if all(len(emb) > 0 for emb in data['embeddings']):
                print("[PASS] All embeddings have non-zero dimensions")
            else:
                print("[FAIL] Some embeddings are empty")
                
            return True
        else:
            print(f"[FAIL] Text embedding request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error testing text embeddings: {e}")
        return False

def test_service_health():
    """Test service health endpoint"""
    print("[TEST] Testing service health...")
    
    try:
        response = requests.get('http://localhost:8004/health')
        if response.status_code == 200:
            data = response.json()
            print("[PASS] Service is healthy")
            print(f"   Model loaded: {data['model_loaded']}")
            print(f"   CUDA available: {data['cuda_available']}")
            print(f"   GPU: {data.get('gpu_name', 'N/A')}")
            print(f"   Device: {data['device']}")
            return True
        else:
            print(f"[FAIL] Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Error checking service health: {e}")
        return False

def main():
    print("CLIP Service Unit Tests")
    print("=" * 50)
    
    # Test service health first
    health_ok = test_service_health()
    print()
    
    # Test text embeddings
    text_ok = test_text_embeddings()
    print()
    
    # Summary
    print("Test Results:")
    print(f"   Health check: {'PASS' if health_ok else 'FAIL'}")
    print(f"   Text embeddings: {'PASS' if text_ok else 'FAIL'}")
    
    if health_ok and text_ok:
        print("[PASS] All tests passed! CLIP text tower is working correctly.")
    else:
        print("[FAIL] Some tests failed. Check the CLIP service implementation.")

if __name__ == "__main__":
    main()