#!/usr/bin/env tsx
/**
 * MCP Integration Script for RAG Evaluation
 * 
 * This script provides MCP tools that can be used by AI agents to:
 * - Run RAG evaluations on their responses
 * - Access evaluation datasets 
 * - Generate performance reports
 * - Benchmark their performance against standard datasets
 */

import { RAGEvaluationBridge } from './evaluation-bridge.js';

/**
 * MCP Tools for RAG Evaluation
 * These would be integrated into the main MCP server
 */
export class MCPRAGEvaluationTools {
    private bridge: RAGEvaluationBridge;

    constructor() {
        this.bridge = new RAGEvaluationBridge();
    }

    /**
     * MCP Tool: evaluate_rag_response
     * Allows agents to evaluate their RAG responses in real-time
     */
    async evaluateRAGResponse(params: {
        query: string;
        retrieved_contexts: string[];
        generated_answer: string;
        metrics?: string[];
    }) {
        const result = await this.bridge.evaluateResponse({
            query: params.query,
            retrieved_contexts: params.retrieved_contexts,
            generated_answer: params.generated_answer,
            metrics: params.metrics || ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
        });

        return {
            tool_result: {
                evaluation_metrics: result.metrics,
                metric_details: result.details,
                summary: {
                    query: result.query,
                    overall_score: Object.values(result.metrics).reduce((a, b) => a + b, 0) / Object.keys(result.metrics).length,
                    recommendations: this.generateRecommendations(result.metrics)
                }
            }
        };
    }

    /**
     * MCP Tool: run_evaluation_benchmark
     * Runs evaluation on standard datasets for comparison
     */
    async runEvaluationBenchmark(params: {
        dataset_name?: string;
        metrics?: string[];
        max_samples?: number;
    }) {
        const datasetName = params.dataset_name || 'yixuantt/MultiHopRAG';
        
        try {
            const result = await this.bridge.batchEvaluateDataset(datasetName, params.metrics);
            
            return {
                tool_result: {
                    benchmark_results: {
                        dataset: result.dataset,
                        evaluated_samples: result.evaluated_samples,
                        aggregate_metrics: result.aggregate_metrics.mean,
                        performance_summary: this.summarizePerformance(result.aggregate_metrics.mean),
                        timestamp: result.timestamp
                    }
                }
            };
        } catch (error) {
            return {
                tool_result: {
                    error: `Benchmark evaluation failed: ${error}`,
                    available_datasets: await this.getAvailableDatasets()
                }
            };
        }
    }

    /**
     * MCP Tool: list_evaluation_datasets
     * Lists available datasets for evaluation
     */
    async listEvaluationDatasets() {
        const [available, local] = await Promise.all([
            this.bridge.listAvailableDatasets(),
            this.bridge.listLocalDatasets()
        ]);

        return {
            tool_result: {
                available_datasets: available.available_datasets,
                local_datasets: local.local_datasets,
                recommendation: "Use 'yixuantt/MultiHopRAG' for multi-hop reasoning evaluation"
            }
        };
    }

    /**
     * MCP Tool: download_evaluation_dataset
     * Downloads a dataset for evaluation
     */
    async downloadEvaluationDataset(params: {
        dataset_name: string;
        max_samples?: number;
    }) {
        try {
            const result = await this.bridge.downloadDataset({
                dataset_name: params.dataset_name,
                split: 'train',
                max_samples: params.max_samples || 100
            });

            return {
                tool_result: {
                    download_status: 'success',
                    dataset: result.dataset,
                    samples_downloaded: result.samples,
                    local_path: result.local_path,
                    message: `Dataset ${params.dataset_name} successfully downloaded with ${result.samples} samples`
                }
            };
        } catch (error) {
            return {
                tool_result: {
                    download_status: 'failed',
                    error: `Failed to download ${params.dataset_name}: ${error}`,
                    available_datasets: await this.getAvailableDatasets()
                }
            };
        }
    }

    /**
     * MCP Tool: generate_evaluation_report
     * Generates a comprehensive evaluation report
     */
    async generateEvaluationReport(params: {
        datasets?: string[];
        metrics?: string[];
        include_recommendations?: boolean;
    }) {
        const datasets = params.datasets || ['yixuantt/MultiHopRAG'];
        const pipelineResult = await this.bridge.runEvaluationPipeline({
            datasets,
            metrics: params.metrics,
            maxSamplesPerDataset: 50
        });

        const report = {
            report_id: pipelineResult.pipeline_id,
            generated_at: new Date().toISOString(),
            summary: pipelineResult.summary,
            detailed_results: pipelineResult.results,
            performance_analysis: this.analyzePerformance(pipelineResult.results),
            recommendations: params.include_recommendations !== false ? 
                this.generateDetailedRecommendations(pipelineResult.results) : undefined
        };

        return {
            tool_result: {
                evaluation_report: report,
                message: `Evaluation report generated for ${datasets.length} datasets with ${report.summary.total_samples} total samples`
            }
        };
    }

    /**
     * Helper: Generate performance recommendations
     */
    private generateRecommendations(metrics: Record<string, number>): string[] {
        const recommendations: string[] = [];
        
        if (metrics.faithfulness < 0.7) {
            recommendations.push("Low faithfulness score indicates answers may not be grounded in the provided contexts - review answer generation for hallucinations");
        }
        
        if (metrics.answer_relevancy < 0.7) {
            recommendations.push("Low answer relevancy suggests responses don't directly address the query - improve answer generation focus");
        }
        
        if (metrics.context_precision < 0.6) {
            recommendations.push("Low context precision means retrieved contexts contain irrelevant information - improve retrieval filtering");
        }
        
        if (metrics.context_recall < 0.6) {
            recommendations.push("Low context recall indicates relevant information may be missing from retrieved contexts - improve retrieval coverage");
        }

        if (recommendations.length === 0) {
            recommendations.push("RAGAS scores are within acceptable ranges - continue monitoring");
        }

        return recommendations;
    }

    /**
     * Helper: Summarize performance levels
     */
    private summarizePerformance(metrics: Record<string, number>): string {
        const avgScore = Object.values(metrics).reduce((a, b) => a + b, 0) / Object.keys(metrics).length;
        
        if (avgScore >= 0.7) return "Excellent performance";
        if (avgScore >= 0.5) return "Good performance";
        if (avgScore >= 0.3) return "Fair performance - needs improvement";
        return "Poor performance - significant improvements needed";
    }

    /**
     * Helper: Analyze performance across multiple datasets
     */
    private analyzePerformance(results: any[]): any {
        const analysis = {
            strongest_metric: "",
            weakest_metric: "",
            consistency: "unknown",
            trend_analysis: "stable"
        };

        if (results.length === 0) return analysis;

        // Calculate metric averages across all datasets
        const metricTotals: Record<string, number> = {};
        const metricCounts: Record<string, number> = {};

        results.forEach(result => {
            Object.entries(result.aggregate_metrics.mean).forEach(([metric, value]) => {
                metricTotals[metric] = (metricTotals[metric] || 0) + value;
                metricCounts[metric] = (metricCounts[metric] || 0) + 1;
            });
        });

        const metricAverages = Object.fromEntries(
            Object.entries(metricTotals).map(([metric, total]) => [
                metric, 
                total / metricCounts[metric]
            ])
        );

        // Find strongest and weakest metrics
        const sortedMetrics = Object.entries(metricAverages).sort(([,a], [,b]) => b - a);
        analysis.strongest_metric = sortedMetrics[0]?.[0] || "unknown";
        analysis.weakest_metric = sortedMetrics[sortedMetrics.length - 1]?.[0] || "unknown";

        return analysis;
    }

    /**
     * Helper: Generate detailed recommendations
     */
    private generateDetailedRecommendations(results: any[]): string[] {
        const recommendations = [
            "Based on evaluation results across multiple datasets:",
            "1. Focus on improving the weakest performing metrics",
            "2. Maintain consistency in performance across different query types",
            "3. Consider dataset-specific optimization strategies",
            "4. Regular evaluation helps track improvement over time"
        ];

        return recommendations;
    }

    /**
     * Helper: Get available datasets
     */
    private async getAvailableDatasets(): Promise<string[]> {
        try {
            const available = await this.bridge.listAvailableDatasets();
            return available.available_datasets.map(d => d.name);
        } catch {
            return ['yixuantt/MultiHopRAG'];
        }
    }

    /**
     * Cleanup resources
     */
    async cleanup() {
        await this.bridge.stopService();
    }
}

/**
 * MCP Tool Definitions
 * These would be registered with the MCP server
 */
export const RAG_EVALUATION_TOOLS = {
    evaluate_rag_response: {
        name: "evaluate_rag_response",
        description: "Evaluate a RAG response using RAGAS metrics (faithfulness, answer relevancy, context precision/recall)",
        inputSchema: {
            type: "object",
            properties: {
                query: { type: "string", description: "The original query" },
                retrieved_contexts: { 
                    type: "array", 
                    items: { type: "string" }, 
                    description: "List of retrieved context passages" 
                },
                generated_answer: { type: "string", description: "The generated answer to evaluate" },
                metrics: { 
                    type: "array", 
                    items: { type: "string" }, 
                    description: "Optional: specific metrics to calculate" 
                }
            },
            required: ["query", "retrieved_contexts", "generated_answer"]
        }
    },

    run_evaluation_benchmark: {
        name: "run_evaluation_benchmark",
        description: "Run evaluation benchmark on a standard dataset for performance comparison",
        inputSchema: {
            type: "object",
            properties: {
                dataset_name: { type: "string", description: "Name of the dataset to benchmark against" },
                metrics: { 
                    type: "array", 
                    items: { type: "string" }, 
                    description: "Specific metrics to evaluate" 
                },
                max_samples: { type: "number", description: "Maximum number of samples to evaluate" }
            }
        }
    },

    list_evaluation_datasets: {
        name: "list_evaluation_datasets", 
        description: "List available datasets for RAG evaluation",
        inputSchema: {
            type: "object",
            properties: {}
        }
    },

    download_evaluation_dataset: {
        name: "download_evaluation_dataset",
        description: "Download a dataset for evaluation purposes",
        inputSchema: {
            type: "object",
            properties: {
                dataset_name: { type: "string", description: "Name of the dataset to download" },
                max_samples: { type: "number", description: "Maximum number of samples to download" }
            },
            required: ["dataset_name"]
        }
    },

    generate_evaluation_report: {
        name: "generate_evaluation_report",
        description: "Generate a comprehensive evaluation report across multiple datasets",
        inputSchema: {
            type: "object",
            properties: {
                datasets: { 
                    type: "array", 
                    items: { type: "string" }, 
                    description: "List of datasets to evaluate" 
                },
                metrics: { 
                    type: "array", 
                    items: { type: "string" }, 
                    description: "Specific metrics to include" 
                },
                include_recommendations: { type: "boolean", description: "Include performance recommendations" }
            }
        }
    }
};

// CLI functionality for testing
async function main() {
    const args = process.argv.slice(2);
    const command = args[0];
    
    if (!command) {
        console.log(`
🔧 MCP RAG Evaluation Tools CLI

Usage: tsx mcp-integration.ts <command> [options]

Commands:
  test-evaluate     Test the evaluate_rag_response tool
  test-benchmark    Test the run_evaluation_benchmark tool
  test-datasets     Test the list_evaluation_datasets tool
  test-download     Test the download_evaluation_dataset tool
  test-report       Test the generate_evaluation_report tool

Examples:
  tsx mcp-integration.ts test-evaluate
  tsx mcp-integration.ts test-benchmark
  tsx mcp-integration.ts test-datasets
        `);
        return;
    }

    const tools = new MCPRAGEvaluationTools();

    try {
        switch (command) {
            case 'test-evaluate':
                console.log('🧪 Testing RAG evaluation...');
                const evalResult = await tools.evaluateRAGResponse({
                    query: "What is the capital of France?",
                    retrieved_contexts: [
                        "France is a country in Europe with rich history and culture.",
                        "Paris is the capital and largest city of France.",
                        "The city of Paris is located on the Seine River."
                    ],
                    generated_answer: "The capital of France is Paris, which is located on the Seine River."
                });
                console.log('📊 Evaluation Result:');
                console.log(JSON.stringify(evalResult, null, 2));
                break;

            case 'test-benchmark':
                console.log('🏁 Testing benchmark evaluation...');
                const benchmarkResult = await tools.runEvaluationBenchmark({
                    dataset_name: 'yixuantt/MultiHopRAG',
                    max_samples: 5
                });
                console.log('📈 Benchmark Result:');
                console.log(JSON.stringify(benchmarkResult, null, 2));
                break;

            case 'test-datasets':
                console.log('📋 Testing dataset listing...');
                const datasetsResult = await tools.listEvaluationDatasets();
                console.log('📚 Available Datasets:');
                console.log(JSON.stringify(datasetsResult, null, 2));
                break;

            case 'test-download':
                console.log('📥 Testing dataset download...');
                const downloadResult = await tools.downloadEvaluationDataset({
                    dataset_name: 'yixuantt/MultiHopRAG',
                    max_samples: 5
                });
                console.log('💾 Download Result:');
                console.log(JSON.stringify(downloadResult, null, 2));
                break;

            case 'test-report':
                console.log('📝 Testing evaluation report generation...');
                const reportResult = await tools.generateEvaluationReport({
                    datasets: ['yixuantt/MultiHopRAG'],
                    include_recommendations: true
                });
                console.log('📋 Evaluation Report:');
                console.log(JSON.stringify(reportResult, null, 2));
                break;

            default:
                console.error(`❌ Unknown command: ${command}`);
        }
    } catch (error) {
        console.error('❌ Error:', error);
    } finally {
        await tools.cleanup();
    }
}

// Run CLI if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main().catch(console.error);
}