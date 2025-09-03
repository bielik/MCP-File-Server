#!/usr/bin/env python3
"""
Qdrant Collection Setup Script
Creates optimized multimodal collections for the MCP Research File Server
"""

import asyncio
import json
from typing import Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    CollectionConfig,
    VectorParams,
    Distance,
    HnswConfig,
    OptimizersConfig,
    QuantizationConfig,
    ScalarQuantization,
    ScalarType,
    WalConfig,
    CollectionStatus
)

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
EMBEDDING_SIZE = 512  # M-CLIP embedding dimension

class QdrantSetup:
    def __init__(self):
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        
    def get_optimized_config(self, collection_type: str) -> Dict[str, Any]:
        """Get optimized configuration for different collection types"""
        base_config = {
            "vectors": VectorParams(
                size=EMBEDDING_SIZE,
                distance=Distance.COSINE  # Best for normalized M-CLIP embeddings
            ),
            "hnsw_config": HnswConfig(
                m=16,  # Optimal for 512d vectors
                ef_construct=200,  # High build-time accuracy
                full_scan_threshold=10000,
                max_indexing_threads=0,  # Use all available threads
                on_disk=False  # Keep in RAM for speed
            ),
            "optimizers_config": OptimizersConfig(
                deleted_threshold=0.2,
                vacuum_min_vector_number=1000,
                default_segment_number=4,  # Parallel processing
                max_segment_size=200000,
                memmap_threshold_kb=200000,
                indexing_threshold_kb=20000,
                flush_interval_sec=5
            ),
            "wal_config": WalConfig(
                wal_capacity_mb=32,
                wal_segments_ahead=0
            ),
            "quantization_config": QuantizationConfig(
                scalar=ScalarQuantization(
                    type=ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True  # Critical for sub-200ms queries
                )
            )
        }
        
        # Adjust configuration based on collection type
        if collection_type == "text_chunks":
            # Text chunks: optimize for semantic search
            base_config["hnsw_config"].ef_construct = 200
            base_config["optimizers_config"].default_segment_number = 4
            
        elif collection_type == "image_embeddings":
            # Images: higher connectivity for visual similarity
            base_config["hnsw_config"].m = 32
            base_config["hnsw_config"].ef_construct = 300
            base_config["optimizers_config"].default_segment_number = 2
            
        elif collection_type == "cross_modal_index":
            # Cross-modal: balanced configuration
            base_config["hnsw_config"].m = 24
            base_config["hnsw_config"].ef_construct = 250
            
        return base_config
        
    async def create_collection(self, collection_name: str, collection_type: str) -> bool:
        """Create a single collection with optimized configuration"""
        try:
            # Check if collection already exists
            existing_collections = self.client.get_collections().collections
            if any(col.name == collection_name for col in existing_collections):
                print(f"✅ Collection '{collection_name}' already exists")
                return True
                
            print(f"🔧 Creating collection: {collection_name}")
            config = self.get_optimized_config(collection_type)
            
            # Create collection
            result = self.client.create_collection(
                collection_name=collection_name,
                vectors_config=config["vectors"],
                hnsw_config=config["hnsw_config"],
                optimizers_config=config["optimizers_config"],
                wal_config=config["wal_config"],
                quantization_config=config["quantization_config"],
                shard_number=1,  # Single shard for local development
                replication_factor=1  # No replication for local setup
            )
            
            if result:
                print(f"✅ Created collection: {collection_name}")
                # Wait for collection to be ready
                await asyncio.sleep(2)
                return True
            else:
                print(f"❌ Failed to create collection: {collection_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating collection {collection_name}: {str(e)}")
            return False
    
    def create_payload_indexes(self, collection_name: str, collection_type: str) -> bool:
        """Create payload indexes for efficient filtering"""
        try:
            indexes = {}
            
            if collection_type == "text_chunks":
                indexes = {
                    "document_id": "keyword",
                    "language": "keyword",
                    "page_number": "integer",
                    "section_title": "text",
                    "document_path": "keyword"
                }
            elif collection_type == "image_embeddings":
                indexes = {
                    "document_id": "keyword",
                    "image_type": "keyword",
                    "page_number": "integer",
                    "document_path": "keyword"
                }
            elif collection_type == "cross_modal_index":
                indexes = {
                    "document_id": "keyword",
                    "source_type": "keyword",
                    "semantic_category": "keyword"
                }
            
            for field_name, field_type in indexes.items():
                try:
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name=field_name,
                        field_schema=field_type
                    )
                    print(f"✅ Created index on {collection_name}.{field_name}")
                except Exception as e:
                    print(f"⚠️  Index {field_name} might already exist: {str(e)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating indexes for {collection_name}: {str(e)}")
            return False
    
    def verify_collections(self) -> Dict[str, Any]:
        """Verify that all collections are properly created and healthy"""
        results = {}
        
        try:
            collections = self.client.get_collections().collections
            
            for collection in collections:
                if collection.name.startswith("mcp_"):
                    info = self.client.get_collection(collection.name)
                    results[collection.name] = {
                        "status": info.status,
                        "points_count": info.points_count,
                        "segments_count": info.segments_count,
                        "vectors_count": info.vectors_count,
                        "config": {
                            "vector_size": info.config.params.vectors.size,
                            "distance": info.config.params.vectors.distance,
                            "hnsw_m": info.config.hnsw_config.m,
                            "quantization_enabled": info.config.quantization_config is not None
                        }
                    }
                    
            return results
            
        except Exception as e:
            print(f"❌ Error verifying collections: {str(e)}")
            return {}
    
    async def setup_all_collections(self) -> bool:
        """Set up all multimodal collections"""
        print("🚀 Setting up Qdrant multimodal collections...")
        
        # Collection definitions
        collections = [
            ("mcp_text_chunks", "text_chunks"),
            ("mcp_image_embeddings", "image_embeddings"),
            ("mcp_cross_modal_index", "cross_modal_index")
        ]
        
        success_count = 0
        
        for collection_name, collection_type in collections:
            success = await self.create_collection(collection_name, collection_type)
            if success:
                # Create payload indexes
                self.create_payload_indexes(collection_name, collection_type)
                success_count += 1
                
        # Verify setup
        print(f"\n📊 Verification Results:")
        verification = self.verify_collections()
        
        for collection_name, info in verification.items():
            status_emoji = "✅" if info["status"] == CollectionStatus.GREEN else "⚠️"
            print(f"{status_emoji} {collection_name}: {info['status']}")
            print(f"   Vector size: {info['config']['vector_size']}")
            print(f"   Distance: {info['config']['distance']}")
            print(f"   HNSW M: {info['config']['hnsw_m']}")
            print(f"   Quantization: {info['config']['quantization_enabled']}")
            print()
        
        if success_count == len(collections):
            print("🎉 All multimodal collections created successfully!")
            return True
        else:
            print(f"⚠️  Created {success_count}/{len(collections)} collections")
            return False

async def main():
    """Main setup function"""
    print("🔧 MCP Research File Server - Qdrant Setup")
    print("=" * 50)
    
    try:
        # Initialize setup
        setup = QdrantSetup()
        
        # Test connection
        print("🔗 Testing Qdrant connection...")
        health = setup.client.get_collections()
        print("✅ Qdrant connection successful")
        
        # Setup collections
        success = await setup.setup_all_collections()
        
        if success:
            print("\n🎯 Setup completed successfully!")
            print("\nNext steps:")
            print("1. Start M-CLIP embedding service")
            print("2. Begin document processing pipeline")
            print("3. Run integration tests")
        else:
            print("\n❌ Setup completed with errors. Please check the logs above.")
            
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {str(e)}")
        print("\nPlease ensure Qdrant is running:")
        print("1. Run: docker-compose up -d qdrant")
        print("2. Wait for health check to pass")
        print("3. Re-run this script")

if __name__ == "__main__":
    asyncio.run(main())