/**
 * Annotation Tools for Creating Ground Truth Datasets
 * Utilities for generating, validating, and managing annotations
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { createHash } from 'crypto';
import {
  Document,
  Chunk,
  ImageAsset,
  TestQuery,
  GroundTruthAnnotation,
  RelevantChunk,
  RelevantImage,
  CrossModalRelation,
  GroundTruthDataset,
  EvaluationSet,
  Annotator
} from './ground-truth-schema';

export class AnnotationToolkit {
  private dataset: GroundTruthDataset;
  private currentAnnotator: Annotator;

  constructor(datasetPath?: string) {
    this.dataset = this.initializeDataset();
    this.currentAnnotator = {
      id: 'system',
      name: 'System Annotator',
      expertise: ['multimodal', 'research'],
      annotations_count: 0
    };
  }

  private initializeDataset(): GroundTruthDataset {
    return {
      version: '1.0.0',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: {
        name: 'Multimodal RAG Ground Truth',
        description: 'Ground truth dataset for evaluating multimodal retrieval',
        domain: 'research',
        languages: ['en'],
        annotators: [],
        annotation_guidelines: 'Annotate all relevant text and image contexts for each query',
        quality_metrics: {
          inter_annotator_agreement: 0,
          coverage: {
            text_chunks: 0,
            images: 0,
            cross_modal: 0
          },
          query_diversity: {
            types: {},
            difficulty_distribution: {}
          }
        }
      },
      documents: [],
      evaluation_sets: [],
      statistics: {
        total_documents: 0,
        total_chunks: 0,
        total_images: 0,
        total_queries: 0,
        total_annotations: 0,
        chunk_coverage: 0,
        image_coverage: 0,
        average_relevant_contexts_per_query: 0,
        multimodal_queries_percentage: 0
      }
    };
  }

  /**
   * Import a document and extract chunks and images
   */
  async importDocument(
    filePath: string,
    chunks: any[],
    images: any[]
  ): Promise<Document> {
    const docId = this.generateId(filePath);
    
    const document: Document = {
      id: docId,
      source_file: filePath,
      type: this.getFileType(filePath),
      metadata: {
        title: path.basename(filePath, path.extname(filePath)),
        tags: []
      },
      chunks: chunks.map((chunk, idx) => ({
        id: `${docId}_chunk_${idx}`,
        document_id: docId,
        type: this.detectChunkType(chunk.content),
        content: chunk.content,
        page_number: chunk.page_number,
        position: {
          start_char: chunk.start || idx * 1000,
          end_char: chunk.end || (idx + 1) * 1000
        },
        metadata: {
          section: chunk.section,
          importance: 'supporting'
        }
      })),
      images: images.map((img, idx) => ({
        id: `${docId}_img_${idx}`,
        document_id: docId,
        file_path: img.path,
        type: this.detectImageType(img),
        caption: img.caption,
        page_number: img.page_number,
        referenced_in_chunks: []
      })),
      cross_references: []
    };

    // Detect cross-references between text and images
    document.cross_references = this.detectCrossReferences(document);
    
    this.dataset.documents.push(document);
    this.updateStatistics();
    
    return document;
  }

  /**
   * Create a test query with ground truth annotations
   */
  async createTestQuery(
    query: string,
    relevantChunks: string[],
    relevantImages: string[],
    options: {
      type?: TestQuery['type'];
      difficulty?: 'easy' | 'medium' | 'hard';
      explanation?: string;
    } = {}
  ): Promise<TestQuery> {
    const queryId = this.generateId(query);
    
    const testQuery: TestQuery = {
      id: queryId,
      query: query,
      type: options.type || this.detectQueryType(query),
      intent: this.extractQueryIntent(query),
      document_ids: this.getDocumentIdsFromChunks(relevantChunks),
      ground_truth: {
        relevant_chunks: relevantChunks.map(chunkId => ({
          chunk_id: chunkId,
          relevance_score: this.calculateRelevanceScore(query, chunkId),
          relevance_type: 'semantic'
        })),
        relevant_images: relevantImages.map(imageId => ({
          image_id: imageId,
          relevance_score: this.calculateImageRelevance(query, imageId),
          relevance_type: 'primary'
        })),
        cross_modal_relationships: this.identifyCrossModalRelations(
          relevantChunks,
          relevantImages
        ),
        explanation: options.explanation
      },
      metadata: {
        difficulty: options.difficulty || 'medium',
        requires_multimodal: relevantImages.length > 0,
        annotator_confidence: 0.9
      }
    };

    return testQuery;
  }

  /**
   * Semi-automated annotation using LLM assistance
   */
  async generateSyntheticAnnotations(
    document: Document,
    numQueries: number = 10
  ): Promise<TestQuery[]> {
    const queries: TestQuery[] = [];
    
    // Generate diverse query types
    const queryTemplates = [
      { template: "What is the {section} of this research?", type: 'factual' as const },
      { template: "Explain the {concept} shown in the figures", type: 'visual' as const },
      { template: "How does {method} work according to the document?", type: 'analytical' as const },
      { template: "Compare {item1} and {item2} from the paper", type: 'comparative' as const },
      { template: "Find all diagrams related to {topic}", type: 'cross_modal' as const }
    ];

    for (let i = 0; i < numQueries; i++) {
      const template = queryTemplates[i % queryTemplates.length];
      const query = this.fillQueryTemplate(template.template, document);
      
      // Identify relevant chunks and images
      const relevantChunks = this.findRelevantChunks(query, document);
      const relevantImages = this.findRelevantImages(query, document);
      
      const testQuery = await this.createTestQuery(
        query,
        relevantChunks,
        relevantImages,
        {
          type: template.type,
          difficulty: this.assessQueryDifficulty(query, relevantChunks.length),
          explanation: `Synthetic query for ${template.type} evaluation`
        }
      );
      
      queries.push(testQuery);
    }
    
    return queries;
  }

  /**
   * Interactive annotation interface for experts
   */
  async startInteractiveAnnotation(
    document: Document,
    annotatorId: string
  ): Promise<void> {
    console.log('Starting interactive annotation session...');
    console.log(`Document: ${document.metadata.title}`);
    console.log(`Chunks: ${document.chunks.length}, Images: ${document.images.length}`);
    
    // This would normally open a web interface or CLI tool
    // For now, we'll create a simple programmatic interface
    
    const annotationSession = {
      document_id: document.id,
      annotator_id: annotatorId,
      start_time: new Date(),
      annotations: [] as GroundTruthAnnotation[]
    };

    // Sample annotation workflow
    const sampleQueries = [
      "What methodology was used in this research?",
      "Show all experimental results with graphs",
      "Explain the data collection process"
    ];

    for (const query of sampleQueries) {
      console.log(`\nQuery: ${query}`);
      console.log('Please select relevant chunks and images...');
      
      // Simulate expert selection
      const relevantChunks = document.chunks
        .filter(chunk => this.isRelevantToQuery(query, chunk.content))
        .slice(0, 3)
        .map(chunk => chunk.id);
        
      const relevantImages = document.images
        .filter(img => this.isImageRelevantToQuery(query, img))
        .slice(0, 2)
        .map(img => img.id);
      
      const annotation: GroundTruthAnnotation = {
        relevant_chunks: relevantChunks.map(id => ({
          chunk_id: id,
          relevance_score: 0.8,
          relevance_type: 'semantic'
        })),
        relevant_images: relevantImages.map(id => ({
          image_id: id,
          relevance_score: 0.7,
          relevance_type: 'supporting'
        })),
        cross_modal_relationships: [],
        explanation: 'Expert annotation'
      };
      
      annotationSession.annotations.push(annotation);
    }
    
    console.log(`\nAnnotation session completed: ${annotationSession.annotations.length} queries annotated`);
  }

  /**
   * Validate annotation quality and consistency
   */
  async validateAnnotations(evaluationSet: EvaluationSet): Promise<{
    valid: boolean;
    issues: string[];
    recommendations: string[];
  }> {
    const issues: string[] = [];
    const recommendations: string[] = [];

    for (const query of evaluationSet.queries) {
      // Check for missing annotations
      if (query.ground_truth.relevant_chunks.length === 0 && 
          query.ground_truth.relevant_images.length === 0) {
        issues.push(`Query ${query.id} has no ground truth annotations`);
      }

      // Check relevance score distribution
      const scores = query.ground_truth.relevant_chunks.map(c => c.relevance_score);
      if (scores.every(s => s === scores[0])) {
        recommendations.push(`Query ${query.id}: Consider varying relevance scores`);
      }

      // Check multimodal queries have both text and images
      if (query.metadata.requires_multimodal) {
        if (query.ground_truth.relevant_images.length === 0) {
          issues.push(`Query ${query.id} marked as multimodal but has no image annotations`);
        }
      }

      // Check cross-modal relationships
      if (query.ground_truth.relevant_chunks.length > 0 && 
          query.ground_truth.relevant_images.length > 0 &&
          query.ground_truth.cross_modal_relationships.length === 0) {
        recommendations.push(`Query ${query.id}: Consider adding cross-modal relationships`);
      }
    }

    // Check dataset coverage
    const coverage = this.calculateCoverage();
    if (coverage.chunk_coverage < 0.3) {
      recommendations.push('Low chunk coverage: Add more diverse queries');
    }
    if (coverage.image_coverage < 0.2) {
      recommendations.push('Low image coverage: Add more visual queries');
    }

    return {
      valid: issues.length === 0,
      issues,
      recommendations
    };
  }

  /**
   * Export dataset to JSON format
   */
  async exportDataset(outputPath: string): Promise<void> {
    await fs.writeFile(
      outputPath,
      JSON.stringify(this.dataset, null, 2),
      'utf-8'
    );
    console.log(`Dataset exported to ${outputPath}`);
  }

  /**
   * Import existing dataset
   */
  async importDataset(datasetPath: string): Promise<void> {
    const data = await fs.readFile(datasetPath, 'utf-8');
    this.dataset = JSON.parse(data);
    console.log(`Dataset imported: ${this.dataset.documents.length} documents, ${this.dataset.evaluation_sets.length} evaluation sets`);
  }

  /**
   * Calculate inter-annotator agreement
   */
  calculateInterAnnotatorAgreement(
    annotations1: GroundTruthAnnotation,
    annotations2: GroundTruthAnnotation
  ): number {
    const chunks1 = new Set(annotations1.relevant_chunks.map(c => c.chunk_id));
    const chunks2 = new Set(annotations2.relevant_chunks.map(c => c.chunk_id));
    
    const intersection = new Set([...chunks1].filter(x => chunks2.has(x)));
    const union = new Set([...chunks1, ...chunks2]);
    
    const chunkAgreement = union.size > 0 ? intersection.size / union.size : 0;
    
    const images1 = new Set(annotations1.relevant_images.map(i => i.image_id));
    const images2 = new Set(annotations2.relevant_images.map(i => i.image_id));
    
    const imgIntersection = new Set([...images1].filter(x => images2.has(x)));
    const imgUnion = new Set([...images1, ...images2]);
    
    const imageAgreement = imgUnion.size > 0 ? imgIntersection.size / imgUnion.size : 0;
    
    return (chunkAgreement + imageAgreement) / 2;
  }

  // Helper methods
  private generateId(input: string): string {
    return createHash('md5').update(input + Date.now()).digest('hex').substring(0, 8);
  }

  private getFileType(filePath: string): Document['type'] {
    const ext = path.extname(filePath).toLowerCase();
    switch (ext) {
      case '.pdf': return 'pdf';
      case '.docx': return 'docx';
      case '.html': return 'html';
      case '.md': return 'markdown';
      default: return 'pdf';
    }
  }

  private detectChunkType(content: string): Chunk['type'] {
    if (content.includes('```') || content.includes('function') || content.includes('class')) {
      return 'code';
    }
    if (content.includes('|') && content.split('\n').length > 2) {
      return 'table';
    }
    if (content.startsWith('Figure') || content.startsWith('Table')) {
      return 'caption';
    }
    return 'text';
  }

  private detectImageType(image: any): ImageAsset['type'] {
    const filename = image.path.toLowerCase();
    if (filename.includes('diagram')) return 'diagram';
    if (filename.includes('chart')) return 'chart';
    if (filename.includes('graph')) return 'graph';
    if (filename.includes('table')) return 'table';
    if (filename.includes('equation') || filename.includes('formula')) return 'equation';
    return 'diagram';
  }

  private detectCrossReferences(document: Document): any[] {
    const references = [];
    
    for (const chunk of document.chunks) {
      const figureRefs = chunk.content.match(/(?:Figure|Fig\.?)\s+\d+/gi) || [];
      const tableRefs = chunk.content.match(/(?:Table)\s+\d+/gi) || [];
      
      for (const ref of [...figureRefs, ...tableRefs]) {
        const imageIdx = parseInt(ref.match(/\d+/)?.[0] || '0') - 1;
        if (document.images[imageIdx]) {
          references.push({
            id: this.generateId(chunk.id + document.images[imageIdx].id),
            type: 'text_to_image',
            source_id: chunk.id,
            target_id: document.images[imageIdx].id,
            relationship: 'references',
            strength: 0.9
          });
          
          document.images[imageIdx].referenced_in_chunks.push(chunk.id);
        }
      }
    }
    
    return references;
  }

  private detectQueryType(query: string): TestQuery['type'] {
    const lower = query.toLowerCase();
    if (lower.includes('what') || lower.includes('when') || lower.includes('where')) {
      return 'factual';
    }
    if (lower.includes('how') || lower.includes('why') || lower.includes('explain')) {
      return 'analytical';
    }
    if (lower.includes('show') || lower.includes('diagram') || lower.includes('figure')) {
      return 'visual';
    }
    if (lower.includes('compare') || lower.includes('difference')) {
      return 'comparative';
    }
    return 'cross_modal';
  }

  private extractQueryIntent(query: string): string {
    return `User wants to ${query.toLowerCase().replace(/^(what|how|why|when|where|show|find|explain)\s+/i, '')}`;
  }

  private calculateRelevanceScore(query: string, chunkId: string): number {
    // Simplified relevance calculation
    return Math.random() * 0.5 + 0.5; // 0.5 to 1.0
  }

  private calculateImageRelevance(query: string, imageId: string): number {
    // Simplified relevance calculation
    return Math.random() * 0.5 + 0.5; // 0.5 to 1.0
  }

  private identifyCrossModalRelations(
    chunkIds: string[],
    imageIds: string[]
  ): CrossModalRelation[] {
    const relations: CrossModalRelation[] = [];
    
    for (const chunkId of chunkIds) {
      for (const imageId of imageIds) {
        if (Math.random() > 0.5) {
          relations.push({
            text_chunk_id: chunkId,
            image_id: imageId,
            relationship_type: 'reference',
            strength: Math.random() * 0.5 + 0.5
          });
        }
      }
    }
    
    return relations;
  }

  private getDocumentIdsFromChunks(chunkIds: string[]): string[] {
    const docIds = new Set<string>();
    for (const chunkId of chunkIds) {
      const docId = chunkId.split('_chunk_')[0];
      docIds.add(docId);
    }
    return Array.from(docIds);
  }

  private fillQueryTemplate(template: string, document: Document): string {
    // Simple template filling
    let query = template;
    query = query.replace('{section}', 'methodology');
    query = query.replace('{concept}', 'experimental setup');
    query = query.replace('{method}', 'data analysis');
    query = query.replace('{item1}', 'baseline');
    query = query.replace('{item2}', 'proposed method');
    query = query.replace('{topic}', 'results');
    return query;
  }

  private assessQueryDifficulty(query: string, numContexts: number): 'easy' | 'medium' | 'hard' {
    if (numContexts <= 2) return 'easy';
    if (numContexts <= 5) return 'medium';
    return 'hard';
  }

  private findRelevantChunks(query: string, document: Document): string[] {
    return document.chunks
      .filter(chunk => this.isRelevantToQuery(query, chunk.content))
      .slice(0, 3)
      .map(chunk => chunk.id);
  }

  private findRelevantImages(query: string, document: Document): string[] {
    return document.images
      .filter(img => this.isImageRelevantToQuery(query, img))
      .slice(0, 2)
      .map(img => img.id);
  }

  private isRelevantToQuery(query: string, content: string): boolean {
    const queryTerms = query.toLowerCase().split(/\s+/);
    const contentLower = content.toLowerCase();
    return queryTerms.some(term => contentLower.includes(term));
  }

  private isImageRelevantToQuery(query: string, image: ImageAsset): boolean {
    const queryLower = query.toLowerCase();
    if (image.caption && image.caption.toLowerCase().includes(queryLower.substring(0, 10))) {
      return true;
    }
    if (queryLower.includes('diagram') && image.type === 'diagram') return true;
    if (queryLower.includes('graph') && image.type === 'graph') return true;
    if (queryLower.includes('chart') && image.type === 'chart') return true;
    return false;
  }

  private calculateCoverage() {
    const annotatedChunks = new Set<string>();
    const annotatedImages = new Set<string>();
    
    for (const evalSet of this.dataset.evaluation_sets) {
      for (const query of evalSet.queries) {
        query.ground_truth.relevant_chunks.forEach(c => annotatedChunks.add(c.chunk_id));
        query.ground_truth.relevant_images.forEach(i => annotatedImages.add(i.image_id));
      }
    }
    
    const totalChunks = this.dataset.documents.reduce((sum, doc) => sum + doc.chunks.length, 0);
    const totalImages = this.dataset.documents.reduce((sum, doc) => sum + doc.images.length, 0);
    
    return {
      chunk_coverage: totalChunks > 0 ? annotatedChunks.size / totalChunks : 0,
      image_coverage: totalImages > 0 ? annotatedImages.size / totalImages : 0
    };
  }

  private updateStatistics() {
    this.dataset.statistics.total_documents = this.dataset.documents.length;
    this.dataset.statistics.total_chunks = this.dataset.documents.reduce(
      (sum, doc) => sum + doc.chunks.length, 0
    );
    this.dataset.statistics.total_images = this.dataset.documents.reduce(
      (sum, doc) => sum + doc.images.length, 0
    );
    
    const coverage = this.calculateCoverage();
    this.dataset.statistics.chunk_coverage = coverage.chunk_coverage;
    this.dataset.statistics.image_coverage = coverage.image_coverage;
    
    this.dataset.updated_at = new Date().toISOString();
  }
}