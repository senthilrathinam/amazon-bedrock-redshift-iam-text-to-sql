"""
FAISS vector store manager for the GenAI Sales Analyst application.
"""
import faiss
import numpy as np
from typing import List, Dict, Any, Optional


class FAISSManager:
    """Manages FAISS vector store operations."""
    
    def __init__(self, bedrock_client, dimension: int = 1024):
        self.bedrock_client = bedrock_client
        self.index = faiss.IndexFlatL2(dimension)
        self.texts = []
        self.metadata = []
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
        """Add texts and their embeddings to the vector store."""
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        embeddings = []
        for text in texts:
            embedding = self.bedrock_client.get_embeddings(text)
            embeddings.append(embedding)
        
        embeddings_array = np.array(embeddings).astype('float32')
        self.index.add(embeddings_array)
        self.texts.extend(texts)
        self.metadata.extend(metadatas)
    
    def similarity_search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Search for similar texts based on the query."""
        if len(self.texts) == 0:
            return []
            
        try:
            query_embedding = self.bedrock_client.get_embeddings(query)
            query_array = np.array([query_embedding]).astype('float32')
            
            k = min(k, len(self.texts))
            if k == 0:
                return []
                
            distances, indices = self.index.search(query_array, k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.texts):
                    results.append({
                        'text': self.texts[idx],
                        'metadata': self.metadata[idx],
                        'distance': float(distances[0][i])
                    })
            return results
        except Exception as e:
            print(f"Error in similarity search: {str(e)}")
            return []
