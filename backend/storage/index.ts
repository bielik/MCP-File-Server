import { QdrantClient } from '@qdrant/js-client-rest';
import { config } from '../config/index.js';
import { logWithContext } from '../utils/logger.js';

export class QdrantVectorStore {
  private client: QdrantClient;

  constructor() {
    this.client = new QdrantClient({
      url: config.qdrant.url,
      ...(config.qdrant.apiKey ? { apiKey: config.qdrant.apiKey } : {}),
    });
  }

  async clearAllCollections(): Promise<void> {
    try {
      // Get all collections
      const collections = await this.client.getCollections();
      
      // Delete collections that match our prefix
      const collectionPrefix = config.qdrant.collectionPrefix;
      for (const collection of collections.collections) {
        if (collection.name.startsWith(collectionPrefix)) {
          await this.client.deleteCollection(collection.name);
          logWithContext.info('Deleted Qdrant collection', { collection: collection.name });
        }
      }

      logWithContext.info('All MCP embeddings collections cleared from Qdrant');
    } catch (error) {
      // If Qdrant is not available, just log a warning
      logWithContext.warn('Failed to clear Qdrant collections (Qdrant may not be running)', { 
        error: (error as Error).message 
      });
    }
  }
}

export default QdrantVectorStore;