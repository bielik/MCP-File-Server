/**
 * Synthetic Query Generator for Ground Truth Dataset
 * Generates diverse test queries from documents using templates and AI assistance
 */

import { Document, TestQuery, Chunk, ImageAsset } from './ground-truth-schema';

interface QueryTemplate {
  pattern: string;
  type: TestQuery['type'];
  difficulty: 'easy' | 'medium' | 'hard';
  requiresMultimodal: boolean;
  contextNeeded: number; // Expected number of relevant contexts
}

export class QueryGenerator {
  private templates: QueryTemplate[] = [
    // Factual queries
    {
      pattern: "What is the {key_term} mentioned in the {section}?",
      type: 'factual',
      difficulty: 'easy',
      requiresMultimodal: false,
      contextNeeded: 1
    },
    {
      pattern: "List the {items} described in this document",
      type: 'factual',
      difficulty: 'easy',
      requiresMultimodal: false,
      contextNeeded: 2
    },
    {
      pattern: "What are the main findings regarding {topic}?",
      type: 'factual',
      difficulty: 'medium',
      requiresMultimodal: false,
      contextNeeded: 3
    },

    // Analytical queries
    {
      pattern: "Explain how {process} works according to the document",
      type: 'analytical',
      difficulty: 'medium',
      requiresMultimodal: false,
      contextNeeded: 3
    },
    {
      pattern: "Why does the author claim that {statement}?",
      type: 'analytical',
      difficulty: 'hard',
      requiresMultimodal: false,
      contextNeeded: 4
    },
    {
      pattern: "Analyze the relationship between {concept1} and {concept2}",
      type: 'analytical',
      difficulty: 'hard',
      requiresMultimodal: false,
      contextNeeded: 5
    },

    // Visual queries
    {
      pattern: "Show the {diagram_type} that illustrates {concept}",
      type: 'visual',
      difficulty: 'easy',
      requiresMultimodal: true,
      contextNeeded: 2
    },
    {
      pattern: "Find all {chart_type} related to {topic}",
      type: 'visual',
      difficulty: 'medium',
      requiresMultimodal: true,
      contextNeeded: 3
    },
    {
      pattern: "What does {figure_reference} demonstrate?",
      type: 'visual',
      difficulty: 'medium',
      requiresMultimodal: true,
      contextNeeded: 3
    },

    // Cross-modal queries
    {
      pattern: "Explain {figure_reference} using both the text and the visual",
      type: 'cross_modal',
      difficulty: 'medium',
      requiresMultimodal: true,
      contextNeeded: 4
    },
    {
      pattern: "How do the {visual_elements} support the claim about {topic}?",
      type: 'cross_modal',
      difficulty: 'hard',
      requiresMultimodal: true,
      contextNeeded: 5
    },
    {
      pattern: "Compare what the text says about {topic} with what is shown in the figures",
      type: 'cross_modal',
      difficulty: 'hard',
      requiresMultimodal: true,
      contextNeeded: 6
    },

    // Comparative queries
    {
      pattern: "Compare {method1} and {method2} discussed in the paper",
      type: 'comparative',
      difficulty: 'medium',
      requiresMultimodal: false,
      contextNeeded: 4
    },
    {
      pattern: "What are the differences between {concept1} and {concept2}?",
      type: 'comparative',
      difficulty: 'medium',
      requiresMultimodal: false,
      contextNeeded: 4
    },
    {
      pattern: "How do the results in {section1} compare to those in {section2}?",
      type: 'comparative',
      difficulty: 'hard',
      requiresMultimodal: true,
      contextNeeded: 6
    }
  ];

  private documentKeywords: Map<string, string[]> = new Map();
  private documentSections: Map<string, string[]> = new Map();
  private documentFigures: Map<string, string[]> = new Map();

  /**
   * Generate diverse queries for a document
   */
  async generateQueries(
    document: Document,
    numQueries: number = 20,
    options: {
      includeEasy?: boolean;
      includeMedium?: boolean;
      includeHard?: boolean;
      multimodalRatio?: number; // 0-1, percentage of multimodal queries
    } = {}
  ): Promise<TestQuery[]> {
    const {
      includeEasy = true,
      includeMedium = true,
      includeHard = true,
      multimodalRatio = 0.4
    } = options;

    // Extract document features
    await this.extractDocumentFeatures(document);

    // Filter templates based on options
    let availableTemplates = this.templates.filter(t => {
      if (!includeEasy && t.difficulty === 'easy') return false;
      if (!includeMedium && t.difficulty === 'medium') return false;
      if (!includeHard && t.difficulty === 'hard') return false;
      return true;
    });

    // Balance multimodal queries
    const numMultimodal = Math.floor(numQueries * multimodalRatio);
    const numTextOnly = numQueries - numMultimodal;

    const multimodalTemplates = availableTemplates.filter(t => t.requiresMultimodal);
    const textTemplates = availableTemplates.filter(t => !t.requiresMultimodal);

    const queries: TestQuery[] = [];

    // Generate text-only queries
    for (let i = 0; i < numTextOnly && textTemplates.length > 0; i++) {
      const template = textTemplates[i % textTemplates.length];
      const query = await this.generateQueryFromTemplate(template, document);
      if (query) {
        queries.push(query);
      }
    }

    // Generate multimodal queries
    for (let i = 0; i < numMultimodal && multimodalTemplates.length > 0; i++) {
      const template = multimodalTemplates[i % multimodalTemplates.length];
      const query = await this.generateQueryFromTemplate(template, document);
      if (query) {
        queries.push(query);
      }
    }

    // Add diversity by varying the queries
    return this.diversifyQueries(queries, document);
  }

  /**
   * Extract key features from document for query generation
   */
  private async extractDocumentFeatures(document: Document) {
    const docId = document.id;

    // Extract keywords from chunks
    const keywords = new Set<string>();
    const sections = new Set<string>();
    const figures = new Set<string>();

    for (const chunk of document.chunks) {
      // Extract section names
      if (chunk.metadata?.section) {
        sections.add(chunk.metadata.section);
      }

      // Extract key terms (simplified - would use NLP in production)
      const terms = this.extractKeyTerms(chunk.content);
      terms.forEach(term => keywords.add(term));

      // Extract figure references
      const figRefs = chunk.content.match(/(?:Figure|Fig\.?|Table)\s+\d+/gi) || [];
      figRefs.forEach(ref => figures.add(ref));
    }

    // Store for template filling
    this.documentKeywords.set(docId, Array.from(keywords));
    this.documentSections.set(docId, Array.from(sections));
    this.documentFigures.set(docId, Array.from(figures));
  }

  /**
   * Generate a query from a template
   */
  private async generateQueryFromTemplate(
    template: QueryTemplate,
    document: Document
  ): Promise<TestQuery | null> {
    const filledQuery = this.fillTemplate(template.pattern, document);
    if (!filledQuery) return null;

    // Find relevant chunks and images based on query
    const relevantChunks = this.findRelevantChunks(
      filledQuery,
      document,
      template.contextNeeded
    );
    
    const relevantImages = template.requiresMultimodal
      ? this.findRelevantImages(filledQuery, document)
      : [];

    // Create test query
    const testQuery: TestQuery = {
      id: this.generateId(filledQuery),
      query: filledQuery,
      type: template.type,
      intent: this.generateIntent(filledQuery, template.type),
      document_ids: [document.id],
      ground_truth: {
        relevant_chunks: relevantChunks.map((chunk, idx) => ({
          chunk_id: chunk.id,
          relevance_score: this.calculateRelevance(idx, relevantChunks.length),
          relevance_type: idx === 0 ? 'exact' : 'semantic'
        })),
        relevant_images: relevantImages.map((img, idx) => ({
          image_id: img.id,
          relevance_score: this.calculateRelevance(idx, relevantImages.length),
          relevance_type: idx === 0 ? 'primary' : 'supporting'
        })),
        cross_modal_relationships: this.generateCrossModalRelations(
          relevantChunks,
          relevantImages,
          document
        ),
        explanation: `Generated from template: ${template.pattern}`
      },
      metadata: {
        difficulty: template.difficulty,
        requires_multimodal: template.requiresMultimodal,
        annotator_confidence: 0.85,
        inter_annotator_agreement: undefined
      }
    };

    return testQuery;
  }

  /**
   * Fill template with document-specific content
   */
  private fillTemplate(pattern: string, document: Document): string | null {
    const keywords = this.documentKeywords.get(document.id) || [];
    const sections = this.documentSections.get(document.id) || [];
    const figures = this.documentFigures.get(document.id) || [];

    if (keywords.length === 0) return null;

    let filled = pattern;

    // Replace placeholders with actual content
    const replacements: Record<string, () => string> = {
      '{key_term}': () => this.randomChoice(keywords),
      '{section}': () => this.randomChoice(sections) || 'introduction',
      '{items}': () => this.randomChoice(['methods', 'results', 'conclusions']),
      '{topic}': () => this.randomChoice(keywords),
      '{process}': () => this.randomChoice(['data collection', 'analysis', 'validation']),
      '{statement}': () => `${this.randomChoice(keywords)} is important`,
      '{concept1}': () => keywords[0] || 'concept A',
      '{concept2}': () => keywords[1] || 'concept B',
      '{diagram_type}': () => this.randomChoice(['diagram', 'flowchart', 'architecture']),
      '{chart_type}': () => this.randomChoice(['graphs', 'charts', 'plots']),
      '{figure_reference}': () => this.randomChoice(figures) || 'Figure 1',
      '{visual_elements}': () => this.randomChoice(['graphs', 'diagrams', 'charts']),
      '{method1}': () => `${this.randomChoice(['baseline', 'traditional', 'standard'])} method`,
      '{method2}': () => `${this.randomChoice(['proposed', 'novel', 'improved'])} method`,
      '{section1}': () => sections[0] || 'section 1',
      '{section2}': () => sections[1] || 'section 2'
    };

    for (const [placeholder, replacer] of Object.entries(replacements)) {
      if (filled.includes(placeholder)) {
        filled = filled.replace(placeholder, replacer());
      }
    }

    return filled;
  }

  /**
   * Find relevant chunks for a query
   */
  private findRelevantChunks(
    query: string,
    document: Document,
    numRequired: number
  ): Chunk[] {
    const queryLower = query.toLowerCase();
    const queryTerms = queryLower.split(/\s+/).filter(t => t.length > 3);

    // Score each chunk
    const scoredChunks = document.chunks.map(chunk => {
      let score = 0;
      const chunkLower = chunk.content.toLowerCase();

      // Term matching
      for (const term of queryTerms) {
        if (chunkLower.includes(term)) {
          score += 1;
        }
      }

      // Section relevance
      if (chunk.metadata?.section && queryLower.includes(chunk.metadata.section.toLowerCase())) {
        score += 2;
      }

      // Importance weighting
      if (chunk.metadata?.importance === 'essential') score += 3;
      if (chunk.metadata?.importance === 'important') score += 2;

      return { chunk, score };
    });

    // Sort by score and return top N
    return scoredChunks
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, numRequired)
      .map(item => item.chunk);
  }

  /**
   * Find relevant images for a query
   */
  private findRelevantImages(query: string, document: Document): ImageAsset[] {
    const queryLower = query.toLowerCase();
    
    // Score each image
    const scoredImages = document.images.map(img => {
      let score = 0;

      // Check if query mentions figure/table references
      if (img.caption) {
        const captionLower = img.caption.toLowerCase();
        if (queryLower.includes('figure') && img.type === 'diagram') score += 3;
        if (queryLower.includes('graph') && img.type === 'graph') score += 3;
        if (queryLower.includes('chart') && img.type === 'chart') score += 3;
        if (queryLower.includes('table') && img.type === 'table') score += 3;
        
        // Caption relevance
        const queryTerms = queryLower.split(/\s+/).filter(t => t.length > 3);
        for (const term of queryTerms) {
          if (captionLower.includes(term)) {
            score += 1;
          }
        }
      }

      // Check if image is referenced in relevant chunks
      if (img.referenced_in_chunks.length > 0) {
        score += 1;
      }

      return { img, score };
    });

    // Return top scoring images
    return scoredImages
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(item => item.img);
  }

  /**
   * Generate cross-modal relationships
   */
  private generateCrossModalRelations(
    chunks: Chunk[],
    images: ImageAsset[],
    document: Document
  ) {
    const relations = [];

    for (const chunk of chunks) {
      for (const img of images) {
        // Check if chunk references the image
        if (img.referenced_in_chunks.includes(chunk.id)) {
          relations.push({
            text_chunk_id: chunk.id,
            image_id: img.id,
            relationship_type: 'reference' as const,
            strength: 0.9
          });
        } else if (chunk.content.toLowerCase().includes('figure') || 
                   chunk.content.toLowerCase().includes('table')) {
          // Weak relationship
          relations.push({
            text_chunk_id: chunk.id,
            image_id: img.id,
            relationship_type: 'description' as const,
            strength: 0.5
          });
        }
      }
    }

    return relations;
  }

  /**
   * Add diversity to generated queries
   */
  private diversifyQueries(queries: TestQuery[], document: Document): TestQuery[] {
    const diversified = [...queries];

    // Add follow-up queries
    for (let i = 0; i < Math.min(3, queries.length); i++) {
      const original = queries[i];
      const followUp = this.generateFollowUpQuery(original, document);
      if (followUp) {
        diversified.push(followUp);
      }
    }

    // Add negation queries
    for (let i = 0; i < Math.min(2, queries.length); i++) {
      const original = queries[queries.length - 1 - i];
      const negation = this.generateNegationQuery(original, document);
      if (negation) {
        diversified.push(negation);
      }
    }

    return diversified;
  }

  /**
   * Generate a follow-up query
   */
  private generateFollowUpQuery(original: TestQuery, document: Document): TestQuery | null {
    const followUpPatterns = [
      "Can you provide more details about ",
      "What evidence supports ",
      "Are there any limitations to "
    ];

    const pattern = this.randomChoice(followUpPatterns);
    const newQuery = pattern + original.query.toLowerCase();

    return {
      ...original,
      id: this.generateId(newQuery),
      query: newQuery,
      metadata: {
        ...original.metadata,
        difficulty: 'hard'
      }
    };
  }

  /**
   * Generate a negation query
   */
  private generateNegationQuery(original: TestQuery, document: Document): TestQuery | null {
    const newQuery = `What information is NOT provided about ${original.query.split(' ').slice(-3).join(' ')}?`;

    return {
      ...original,
      id: this.generateId(newQuery),
      query: newQuery,
      type: 'analytical',
      ground_truth: {
        ...original.ground_truth,
        relevant_chunks: [], // Empty for negation queries
        relevant_images: []
      },
      metadata: {
        ...original.metadata,
        difficulty: 'hard'
      }
    };
  }

  // Helper methods
  private extractKeyTerms(text: string): string[] {
    // Simplified keyword extraction
    const stopWords = new Set(['the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in', 'for', 'with', 'by', 'from', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'over']);
    
    const words = text.toLowerCase()
      .replace(/[^a-z\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 4 && !stopWords.has(word));

    // Get unique terms
    const termCounts = new Map<string, number>();
    for (const word of words) {
      termCounts.set(word, (termCounts.get(word) || 0) + 1);
    }

    // Return top terms
    return Array.from(termCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([term]) => term);
  }

  private generateId(input: string): string {
    return `query_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateIntent(query: string, type: TestQuery['type']): string {
    const intents: Record<TestQuery['type'], string> = {
      'factual': 'Find specific information or facts',
      'analytical': 'Understand relationships and reasoning',
      'visual': 'Locate and interpret visual content',
      'cross_modal': 'Connect textual and visual information',
      'comparative': 'Compare and contrast different elements'
    };
    return intents[type] + ': ' + query;
  }

  private calculateRelevance(index: number, total: number): number {
    // Higher relevance for earlier results
    return Math.max(0.5, 1.0 - (index * 0.15));
  }

  private randomChoice<T>(array: T[]): T {
    return array[Math.floor(Math.random() * array.length)];
  }
}