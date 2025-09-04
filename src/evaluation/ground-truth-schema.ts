/**
 * Ground Truth Dataset Schema for Multimodal RAG Evaluation
 * Defines the structure for comprehensive evaluation datasets including
 * text, images, and cross-modal relationships
 */

export interface GroundTruthDataset {
  version: string;
  created_at: string;
  updated_at: string;
  metadata: DatasetMetadata;
  documents: Document[];
  evaluation_sets: EvaluationSet[];
  statistics: DatasetStatistics;
}

export interface DatasetMetadata {
  name: string;
  description: string;
  domain: 'research' | 'academic' | 'technical' | 'general';
  languages: string[];
  annotators: Annotator[];
  annotation_guidelines: string;
  quality_metrics: QualityMetrics;
}

export interface Document {
  id: string;
  source_file: string;
  type: 'pdf' | 'docx' | 'html' | 'markdown';
  metadata: {
    title: string;
    authors?: string[];
    publication_date?: string;
    category?: string;
    tags?: string[];
  };
  chunks: Chunk[];
  images: ImageAsset[];
  cross_references: CrossReference[];
}

export interface Chunk {
  id: string;
  document_id: string;
  type: 'text' | 'table' | 'code' | 'caption';
  content: string;
  page_number?: number;
  position: {
    start_char: number;
    end_char: number;
  };
  embedding?: number[];
  metadata: {
    section?: string;
    subsection?: string;
    importance: 'essential' | 'important' | 'supporting' | 'tangential';
  };
}

export interface ImageAsset {
  id: string;
  document_id: string;
  file_path: string;
  type: 'diagram' | 'chart' | 'graph' | 'photo' | 'table' | 'equation';
  caption?: string;
  page_number?: number;
  embedding?: number[];
  ocr_text?: string;
  referenced_in_chunks: string[]; // Chunk IDs that reference this image
}

export interface CrossReference {
  id: string;
  type: 'text_to_image' | 'image_to_text' | 'text_to_text';
  source_id: string;
  target_id: string;
  relationship: 'describes' | 'references' | 'supports' | 'contradicts';
  strength: number; // 0-1 relevance score
}

export interface EvaluationSet {
  id: string;
  name: string;
  queries: TestQuery[];
  metrics: EvaluationMetrics;
}

export interface TestQuery {
  id: string;
  query: string;
  type: 'factual' | 'analytical' | 'visual' | 'cross_modal' | 'comparative';
  intent: string; // Human-readable description of what the query seeks
  document_ids: string[]; // Documents that contain relevant information
  ground_truth: GroundTruthAnnotation;
  metadata: {
    difficulty: 'easy' | 'medium' | 'hard';
    requires_multimodal: boolean;
    annotator_confidence: number; // 0-1
    inter_annotator_agreement?: number; // 0-1
  };
}

export interface GroundTruthAnnotation {
  relevant_chunks: RelevantChunk[];
  relevant_images: RelevantImage[];
  cross_modal_relationships: CrossModalRelation[];
  expected_answer?: string; // Optional: for answer quality evaluation
  explanation?: string; // Why these contexts are relevant
}

export interface RelevantChunk {
  chunk_id: string;
  relevance_score: number; // 0-1, where 1 is essential
  relevance_type: 'exact' | 'semantic' | 'supporting' | 'contextual';
  excerpt?: string; // Specific part if only portion is relevant
}

export interface RelevantImage {
  image_id: string;
  relevance_score: number; // 0-1
  relevance_type: 'primary' | 'supporting' | 'illustrative';
  regions_of_interest?: ROI[]; // Specific parts of image if applicable
}

export interface ROI {
  x: number;
  y: number;
  width: number;
  height: number;
  description: string;
}

export interface CrossModalRelation {
  text_chunk_id: string;
  image_id: string;
  relationship_type: 'description' | 'reference' | 'evidence' | 'example';
  strength: number; // 0-1
}

export interface Annotator {
  id: string;
  name: string;
  expertise: string[];
  annotations_count: number;
  agreement_score?: number; // Agreement with other annotators
}

export interface QualityMetrics {
  inter_annotator_agreement: number;
  coverage: {
    text_chunks: number;
    images: number;
    cross_modal: number;
  };
  query_diversity: {
    types: Record<string, number>;
    difficulty_distribution: Record<string, number>;
  };
}

export interface DatasetStatistics {
  total_documents: number;
  total_chunks: number;
  total_images: number;
  total_queries: number;
  total_annotations: number;
  chunk_coverage: number; // Percentage of chunks with annotations
  image_coverage: number; // Percentage of images with annotations
  average_relevant_contexts_per_query: number;
  multimodal_queries_percentage: number;
}

export interface EvaluationMetrics {
  context_recall: {
    text: number;
    image: number;
    combined: number;
  };
  context_precision: {
    text: number;
    image: number;
    combined: number;
  };
  context_relevance: {
    text: number;
    image: number;
    cross_modal: number;
  };
}

// Evaluation result structure
export interface EvaluationResult {
  query_id: string;
  retrieved_chunks: string[];
  retrieved_images: string[];
  ground_truth_chunks: string[];
  ground_truth_images: string[];
  metrics: {
    recall: number;
    precision: number;
    f1_score: number;
    ndcg: number; // Normalized Discounted Cumulative Gain
    map: number; // Mean Average Precision
  };
  multimodal_metrics: {
    text_recall: number;
    image_recall: number;
    cross_modal_accuracy: number;
    relevance_distribution: {
      essential_retrieved: number;
      important_retrieved: number;
      supporting_retrieved: number;
    };
  };
}