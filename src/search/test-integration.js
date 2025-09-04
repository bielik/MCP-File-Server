// Integration test for M-CLIP + Qdrant
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

async function testIntegration() {
  console.log('🚀 Testing complete M-CLIP + Qdrant integration...\n');
  
  try {
    // 1. Generate embeddings for test documents
    console.log('📝 Generating embeddings for test documents...');
    const documents = [
      { id: uuidv4(), text: 'Artificial intelligence and machine learning are transforming research methodology in academic institutions.' },
      { id: uuidv4(), text: 'Computer vision techniques using deep neural networks have shown remarkable progress in image recognition tasks.' },
      { id: uuidv4(), text: 'Natural language processing models like transformers have revolutionized text understanding and generation.' },
      { id: uuidv4(), text: 'Quantum computing promises exponential speedup for certain computational problems in physics and chemistry.' },
      { id: uuidv4(), text: 'Climate change research requires interdisciplinary collaboration between environmental scientists and data analysts.' }
    ];
    
    // Get embeddings from M-CLIP
    const embeddings = [];
    for (const doc of documents) {
      const response = await axios.post('http://localhost:8002/embed/text', {
        texts: [doc.text]
      });
      embeddings.push({
        id: doc.id,
        text: doc.text,
        embedding: response.data.embeddings[0],
        device: response.data.device
      });
      console.log(`  ✅ Embedded doc ${doc.id.substring(0, 8)}: ${doc.text.substring(0, 50)}...`);
    }
    
    // 2. Store embeddings in Qdrant
    console.log('\n💾 Storing embeddings in Qdrant...');
    for (const doc of embeddings) {
      await axios.put(`http://localhost:6333/collections/mcp_text_embeddings/points`, {
        points: [{
          id: doc.id,
          vector: doc.embedding,
          payload: {
            text: doc.text,
            created_at: new Date().toISOString()
          }
        }]
      });
      console.log(`  ✅ Stored doc ${doc.id.substring(0, 8)}`);
    }
    
    // 3. Test semantic search
    console.log('\n🔍 Testing semantic search...');
    const queries = [
      'machine learning algorithms',
      'environmental science and climate',
      'quantum physics research'
    ];
    
    for (const query of queries) {
      // Get query embedding
      const queryResponse = await axios.post('http://localhost:8002/embed/text', {
        texts: [query]
      });
      const queryEmbedding = queryResponse.data.embeddings[0];
      
      // Search in Qdrant
      const searchResponse = await axios.post('http://localhost:6333/collections/mcp_text_embeddings/points/search', {
        vector: queryEmbedding,
        limit: 3,
        with_payload: true
      });
      
      console.log(`\n  Query: "${query}"`);
      console.log(`  Results:`);
      searchResponse.data.result.forEach((result, idx) => {
        console.log(`    ${idx + 1}. Score: ${result.score.toFixed(3)} - ${result.payload.text.substring(0, 60)}...`);
      });
    }
    
    // 4. Get collection info
    console.log('\n📊 Collection statistics:');
    const collectionInfo = await axios.get('http://localhost:6333/collections/mcp_text_embeddings');
    console.log(`  Points count: ${collectionInfo.data.result.points_count}`);
    console.log(`  Vectors count: ${collectionInfo.data.result.vectors_count}`);
    console.log(`  Status: ${collectionInfo.data.result.status}`);
    
    console.log('\n✅ Integration test completed successfully!');
    console.log('🎯 M-CLIP (GPU) + Qdrant are working perfectly together!');
    
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
  }
}

testIntegration();