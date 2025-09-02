#!/usr/bin/env tsx
/**
 * RAG Evaluation Bridge - TypeScript to Python Communication
 * 
 * This module provides a TypeScript interface to communicate with the Python
 * RAG evaluation service, enabling seamless integration between our Node.js/TS
 * MCP server and the Python evaluation backend.
 */

import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import axios, { AxiosResponse } from 'axios';
import fs from 'fs/promises';
import { setTimeout } from 'timers/promises';

// Types for RAG evaluation
export interface EvaluationRequest {
    query: string;
    retrieved_contexts: string[];
    generated_answer: string;
    ground_truth?: string;
    metrics?: string[];
}

export interface EvaluationResult {
    query: string;
    metrics: Record<string, number>;
    details: Record<string, any>;
}

export interface DatasetDownloadRequest {
    dataset_name: string;
    subset?: string;
    split?: string;
    max_samples?: number;
}

export interface DatasetInfo {
    dataset_name: string;
    samples: number;
    local_path: string;
    features: string[];
    downloaded_at: string;
}

export interface BatchEvaluationResult {
    dataset: string;
    evaluated_samples: number;
    individual_results: Array<{
        sample_id: number;
        query: string;
        metrics: Record<string, number>;
    }>;
    aggregate_metrics: {
        mean: Record<string, number>;
        std: Record<string, number>;
        min: Record<string, number>;
        max: Record<string, number>;
    };
    timestamp: string;
}

/**
 * RAG Evaluation Bridge - Manages Python service communication
 */
export class RAGEvaluationBridge {
    private pythonProcess: ChildProcess | null = null;
    private readonly serviceUrl = 'http://127.0.0.1:8001';
    private readonly pythonScriptPath: string;
    private readonly pythonEnvPath: string;
    private isServiceRunning = false;

    constructor() {
        const currentDir = path.dirname(import.meta.url.replace('file://', ''));
        this.pythonScriptPath = path.join(currentDir, '..', 'python', 'ragas_service.py');
        this.pythonEnvPath = path.join(currentDir, '..', 'python-env', 'Scripts', 'python.exe');
    }

    /**
     * Start the Python evaluation service
     */
    async startService(): Promise<void> {
        // Check if service is already running externally
        try {
            const response = await axios.get(`${this.serviceUrl}/health`, { timeout: 2000 });
            if (response.status === 200) {
                console.log('🔍 RAGAS service is already running externally');
                this.isServiceRunning = true;
                return;
            }
        } catch (error) {
            // Service not running, we'll start it
        }

        if (this.isServiceRunning) {
            console.log('🔍 RAG Evaluation service is already running');
            return;
        }

        console.log('🚀 Starting Python RAG Evaluation service...');
        
        try {
            // Check if Python script exists
            await fs.access(this.pythonScriptPath);
            await fs.access(this.pythonEnvPath);
        } catch (error) {
            throw new Error(`Python service files not found: ${error}`);
        }

        // Start Python process
        this.pythonProcess = spawn(this.pythonEnvPath, [this.pythonScriptPath], {
            cwd: path.dirname(this.pythonScriptPath),
            stdio: ['pipe', 'pipe', 'pipe'],
            shell: false
        });

        // Handle process events
        this.pythonProcess.stdout?.on('data', (data) => {
            console.log(`🐍 Python service: ${data.toString().trim()}`);
        });

        this.pythonProcess.stderr?.on('data', (data) => {
            console.error(`❌ Python service error: ${data.toString().trim()}`);
        });

        this.pythonProcess.on('close', (code) => {
            console.log(`🔍 Python evaluation service exited with code ${code}`);
            this.isServiceRunning = false;
            this.pythonProcess = null;
        });

        // Wait for service to be ready
        console.log('⏳ Waiting for Python service to be ready...');
        await this.waitForService();
        this.isServiceRunning = true;
        console.log('✅ Python RAG Evaluation service is ready');
    }

    /**
     * Stop the Python evaluation service
     */
    async stopService(): Promise<void> {
        if (!this.pythonProcess) {
            return;
        }

        console.log('🛑 Stopping Python RAG Evaluation service...');
        this.pythonProcess.kill('SIGTERM');
        
        // Wait for graceful shutdown
        await setTimeout(2000);
        
        if (this.pythonProcess && !this.pythonProcess.killed) {
            console.log('🔥 Force killing Python service...');
            this.pythonProcess.kill('SIGKILL');
        }
        
        this.isServiceRunning = false;
        this.pythonProcess = null;
        console.log('✅ Python service stopped');
    }

    /**
     * Wait for the Python service to become available
     */
    private async waitForService(maxRetries = 30, retryDelay = 1000): Promise<void> {
        for (let i = 0; i < maxRetries; i++) {
            try {
                const response = await axios.get(`${this.serviceUrl}/health`, { timeout: 5000 });
                if (response.data.status === 'healthy') {
                    return;
                }
            } catch (error) {
                // Service not ready yet
                if (i === maxRetries - 1) {
                    throw new Error(`Python service failed to start after ${maxRetries} retries`);
                }
                await setTimeout(retryDelay);
            }
        }
    }

    /**
     * Ensure service is running before making requests
     */
    private async ensureServiceRunning(): Promise<void> {
        if (!this.isServiceRunning) {
            await this.startService();
        }
    }

    /**
     * Make HTTP request to Python service
     */
    private async makeRequest<T>(endpoint: string, method = 'GET', data?: any): Promise<T> {
        await this.ensureServiceRunning();
        
        try {
            let response: AxiosResponse<T>;
            
            if (method === 'GET') {
                response = await axios.get(`${this.serviceUrl}${endpoint}`, { timeout: 30000 });
            } else if (method === 'POST') {
                response = await axios.post(`${this.serviceUrl}${endpoint}`, data, { timeout: 30000 });
            } else {
                throw new Error(`Unsupported HTTP method: ${method}`);
            }
            
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                throw new Error(`Python service error: ${error.response?.data?.detail || error.message}`);
            }
            throw error;
        }
    }

    /**
     * Get service health status
     */
    async getHealth(): Promise<{ status: string; service: string }> {
        return this.makeRequest('/health');
    }

    /**
     * List available datasets for download
     */
    async listAvailableDatasets(): Promise<{ available_datasets: any[] }> {
        return this.makeRequest('/datasets');
    }

    /**
     * Download a dataset for evaluation
     */
    async downloadDataset(request: DatasetDownloadRequest): Promise<{
        status: string;
        dataset: string;
        samples: number;
        local_path: string;
        metadata_path: string;
    }> {
        console.log(`📥 Downloading dataset: ${request.dataset_name}`);
        const result = await this.makeRequest('/datasets/download', 'POST', request);
        console.log(`✅ Dataset downloaded: ${request.dataset_name} (${result.samples} samples)`);
        return result;
    }

    /**
     * List locally downloaded datasets
     */
    async listLocalDatasets(): Promise<{ local_datasets: DatasetInfo[] }> {
        return this.makeRequest('/datasets/local');
    }

    /**
     * Evaluate a single RAG response using RAGAS
     */
    async evaluateResponse(request: EvaluationRequest): Promise<EvaluationResult> {
        // Convert to RAGAS API format
        const ragasRequest = {
            question: request.query,
            contexts: request.retrieved_contexts,
            answer: request.generated_answer,
            ground_truth: request.ground_truth,
            metrics: request.metrics || ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
        };
        
        const result = await this.makeRequest('/evaluate', 'POST', ragasRequest);
        
        // Convert back to standard format
        return {
            query: result.question,
            metrics: result.metrics,
            details: result.evaluation_details
        };
    }

    /**
     * Perform batch evaluation on a dataset
     */
    async batchEvaluateDataset(
        datasetName: string, 
        metrics?: string[]
    ): Promise<BatchEvaluationResult> {
        console.log(`🔍 Starting batch evaluation of dataset: ${datasetName}`);
        const params = new URLSearchParams();
        params.append('dataset_name', datasetName);
        if (metrics) {
            metrics.forEach(metric => params.append('metrics', metric));
        }
        
        const result = await this.makeRequest<BatchEvaluationResult>(
            `/batch-evaluate?${params.toString()}`, 
            'POST'
        );
        
        console.log(`✅ Batch evaluation completed: ${result.evaluated_samples} samples`);
        return result;
    }

    /**
     * Run comprehensive evaluation pipeline
     */
    async runEvaluationPipeline(config: {
        datasets: string[];
        metrics?: string[];
        maxSamplesPerDataset?: number;
    }): Promise<{
        pipeline_id: string;
        results: BatchEvaluationResult[];
        summary: {
            total_datasets: number;
            total_samples: number;
            average_metrics: Record<string, number>;
        };
    }> {
        const pipelineId = `eval_${Date.now()}`;
        const results: BatchEvaluationResult[] = [];
        
        console.log(`🔄 Starting evaluation pipeline: ${pipelineId}`);
        console.log(`📋 Datasets to evaluate: ${config.datasets.join(', ')}`);

        // Download datasets if needed
        for (const datasetName of config.datasets) {
            try {
                const localDatasets = await this.listLocalDatasets();
                const exists = localDatasets.local_datasets.some(
                    d => d.dataset_name.includes(datasetName.replace('/', '_'))
                );
                
                if (!exists) {
                    await this.downloadDataset({
                        dataset_name: datasetName,
                        split: 'train',
                        max_samples: config.maxSamplesPerDataset
                    });
                }
                
                // Evaluate dataset
                const result = await this.batchEvaluateDataset(datasetName, config.metrics);
                results.push(result);
                
            } catch (error) {
                console.error(`❌ Failed to evaluate dataset ${datasetName}:`, error);
                // Continue with other datasets
            }
        }

        // Calculate summary statistics
        const totalSamples = results.reduce((sum, r) => sum + r.evaluated_samples, 0);
        const averageMetrics: Record<string, number> = {};
        
        if (results.length > 0) {
            const allMetrics = Object.keys(results[0].aggregate_metrics.mean);
            for (const metric of allMetrics) {
                const values = results.map(r => r.aggregate_metrics.mean[metric]).filter(v => !isNaN(v));
                averageMetrics[metric] = values.length > 0 
                    ? values.reduce((sum, v) => sum + v, 0) / values.length 
                    : 0;
            }
        }

        const summary = {
            pipeline_id: pipelineId,
            results,
            summary: {
                total_datasets: results.length,
                total_samples: totalSamples,
                average_metrics: averageMetrics
            }
        };

        console.log(`✅ Evaluation pipeline completed: ${pipelineId}`);
        console.log(`📊 Summary: ${results.length} datasets, ${totalSamples} samples`);
        
        return summary;
    }
}

// Utility functions for easy usage
export async function createEvaluationBridge(): Promise<RAGEvaluationBridge> {
    const bridge = new RAGEvaluationBridge();
    await bridge.startService();
    return bridge;
}

export async function quickEvaluation(
    query: string,
    contexts: string[],
    answer: string,
    metrics?: string[]
): Promise<EvaluationResult> {
    const bridge = await createEvaluationBridge();
    
    try {
        return await bridge.evaluateResponse({
            query,
            retrieved_contexts: contexts,
            generated_answer: answer,
            metrics: metrics || ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
        });
    } finally {
        await bridge.stopService();
    }
}

// CLI functionality
async function main() {
    const args = process.argv.slice(2);
    const command = args[0];
    
    if (!command) {
        console.log(`
🔍 RAG Evaluation Bridge CLI

Usage: tsx evaluation-bridge.ts <command> [options]

Commands:
  start      Start the Python evaluation service
  stop       Stop the Python evaluation service  
  test       Run a test evaluation
  download   Download a dataset (requires dataset name)
  evaluate   Run batch evaluation (requires dataset name)
  pipeline   Run full evaluation pipeline

Examples:
  tsx evaluation-bridge.ts start
  tsx evaluation-bridge.ts download BeIR/nq
  tsx evaluation-bridge.ts evaluate BeIR/nq
  tsx evaluation-bridge.ts pipeline
        `);
        return;
    }

    const bridge = new RAGEvaluationBridge();

    try {
        switch (command) {
            case 'start':
                await bridge.startService();
                console.log('Service started. Press Ctrl+C to stop.');
                process.on('SIGINT', async () => {
                    await bridge.stopService();
                    process.exit(0);
                });
                break;

            case 'stop':
                await bridge.stopService();
                break;

            case 'test':
                await bridge.startService();
                const testResult = await bridge.evaluateResponse({
                    query: "What is the capital of France?",
                    retrieved_contexts: ["France is a country in Europe.", "Paris is the capital city of France."],
                    generated_answer: "The capital of France is Paris.",
                    ground_truth: "Paris",
                    metrics: ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
                });
                console.log('🧪 Test evaluation result:', JSON.stringify(testResult, null, 2));
                await bridge.stopService();
                break;

            case 'download':
                const datasetName = args[1];
                if (!datasetName) {
                    console.error('❌ Please provide dataset name');
                    return;
                }
                await bridge.startService();
                await bridge.downloadDataset({ dataset_name: datasetName });
                await bridge.stopService();
                break;

            case 'evaluate':
                const evalDataset = args[1];
                if (!evalDataset) {
                    console.error('❌ Please provide dataset name');
                    return;
                }
                await bridge.startService();
                const evalResult = await bridge.batchEvaluateDataset(evalDataset);
                console.log('📊 Evaluation results:', JSON.stringify(evalResult.aggregate_metrics, null, 2));
                await bridge.stopService();
                break;

            case 'pipeline':
                await bridge.startService();
                const pipelineResult = await bridge.runEvaluationPipeline({
                    datasets: ['BeIR/nq'],
                    maxSamplesPerDataset: 50
                });
                console.log('🔄 Pipeline results:', JSON.stringify(pipelineResult.summary, null, 2));
                await bridge.stopService();
                break;

            default:
                console.error(`❌ Unknown command: ${command}`);
        }
    } catch (error) {
        console.error('❌ Error:', error);
        await bridge.stopService();
        process.exit(1);
    }
}

// Run CLI if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main().catch(console.error);
}