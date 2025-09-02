#!/usr/bin/env node

/**
 * Simple test script for RAGAS MCP integration
 * Tests the RAGAS service directly without service management complexity
 */

import axios from 'axios';

const SERVICE_URL = 'http://127.0.0.1:8001';

async function testRAGASEvaluation() {
    console.log('🧪 Testing RAGAS MCP Integration...');
    
    try {
        // Test health check
        const healthResponse = await axios.get(`${SERVICE_URL}/health`, { timeout: 5000 });
        console.log('✅ Health Check:', healthResponse.data.status);
        
        // Test single evaluation
        const evalRequest = {
            question: "What is the capital of France?",
            contexts: [
                "France is a country in Western Europe.",
                "Paris is the capital and most populous city of France."
            ],
            answer: "The capital of France is Paris.",
            ground_truth: "Paris",
            metrics: ["faithfulness", "answer_relevancy"]
        };
        
        console.log('🔄 Running RAGAS evaluation...');
        const evalResponse = await axios.post(`${SERVICE_URL}/evaluate`, evalRequest, { 
            timeout: 30000,
            headers: { 'Content-Type': 'application/json' }
        });
        
        console.log('✅ RAGAS Evaluation Success!');
        console.log(`📊 Question: ${evalResponse.data.question}`);
        console.log('📈 Metrics:');
        for (const [metric, score] of Object.entries(evalResponse.data.metrics)) {
            console.log(`   - ${metric}: ${score.toFixed(3)}`);
        }
        console.log(`🔬 Framework: ${evalResponse.data.evaluation_details.evaluation_framework}`);
        console.log(`🤖 Model: ${evalResponse.data.evaluation_details.llm_model}`);
        
        // Test ground truth endpoint
        const groundTruthResponse = await axios.get(`${SERVICE_URL}/ground-truth`, { timeout: 5000 });
        console.log(`✅ Ground Truth Dataset: ${groundTruthResponse.data.ground_truth_entries} entries`);
        
        console.log('\n🎉 All RAGAS MCP tests passed!');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        if (error.response?.data) {
            console.error('   Response:', error.response.data);
        }
        process.exit(1);
    }
}

// Run test
testRAGASEvaluation().catch(console.error);