// Simple test to verify basic connectivity
import axios from 'axios';

async function quickTest() {
  console.log('🧪 Quick connectivity test...');
  
  try {
    // Test M-CLIP
    const mclipResponse = await axios.get('http://localhost:8002/health');
    console.log('✅ M-CLIP:', mclipResponse.data);
    
    // Test Qdrant (no health endpoint, use collections)
    const qdrantResponse = await axios.get('http://localhost:6333/collections');
    console.log('✅ Qdrant collections:', qdrantResponse.data.result.collections.map(c => c.name));
    
    // Test M-CLIP embedding
    const embedResponse = await axios.post('http://localhost:8002/embed/text', {
      texts: ['test embedding']
    });
    console.log('✅ M-CLIP embedding:', embedResponse.data.embeddings[0].slice(0, 5), '...');
    
    console.log('🎉 All services are working!');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

quickTest();