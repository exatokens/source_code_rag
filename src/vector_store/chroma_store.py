"""
ChromaDB vector store for code embeddings

ChromaDB advantages:
- Local-first (no API keys needed)
- Fast similarity search
- Persistent storage
- Metadata filtering
- Easy to use
"""
import os
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


class ChromaVectorStore:
    """
    Vector store using ChromaDB for code embeddings

    Storage structure:
    - Collection per repository
    - Each document = one code chunk (function/class)
    - Metadata: filepath, line numbers, language, type
    - Embedding: 384-dim vector from sentence-transformers
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "code_embeddings"
    ):
        """
        Initialize ChromaDB vector store

        Args:
            persist_directory: Where to store the database
            collection_name: Name of the collection (usually repo name)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Initialize ChromaDB client
        print(f"🔄 Initializing ChromaDB at {persist_directory}")
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Create or get collection
        # Note: ChromaDB will use the default embedding function unless we provide embeddings
        # We'll provide pre-computed embeddings from sentence-transformers
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Code embeddings for semantic search"}
        )

        print(f"✅ Collection '{collection_name}' ready ({self.collection.count()} documents)")

    def add_embeddings(
        self,
        embeddings: List[List[float]],
        metadatas: List[Dict],
        ids: Optional[List[str]] = None,
        documents: Optional[List[str]] = None
    ):
        """
        Add embeddings to the collection

        Args:
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts (filepath, line numbers, etc.)
            ids: Optional list of unique IDs (generated if not provided)
            documents: Optional list of text content (for display)
        """
        # Generate IDs if not provided
        if ids is None:
            ids = [f"{meta.get('filepath', 'unknown')}::{meta.get('qualified_name', str(i))}"
                   for i, meta in enumerate(metadatas)]

        # Convert numpy arrays to lists if needed
        embeddings_list = [
            emb.tolist() if hasattr(emb, 'tolist') else emb
            for emb in embeddings
        ]

        # Add to collection
        self.collection.add(
            embeddings=embeddings_list,
            metadatas=metadatas,
            ids=ids,
            documents=documents
        )

        print(f"✅ Added {len(embeddings)} embeddings to collection")
        print(f"   Total documents: {self.collection.count()}")

    def query(
        self,
        query_embedding: Any,
        n_results: int = 10,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> Dict:
        """
        Query for similar code chunks

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filter (e.g., {"language": "python"})
            where_document: Document content filter

        Returns:
            Query results with ids, distances, metadatas, documents
        """
        # Convert numpy array to list if needed
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document
        )

        return results

    def get_by_id(self, ids: List[str]) -> Dict:
        """
        Get documents by their IDs

        Args:
            ids: List of document IDs

        Returns:
            Documents with metadata
        """
        return self.collection.get(ids=ids)

    def delete_collection(self):
        """Delete the entire collection (use with caution!)"""
        self.client.delete_collection(name=self.collection_name)
        print(f"🗑️  Deleted collection '{self.collection_name}'")

    def update_embedding(self, id: str, embedding: Any, metadata: Dict, document: Optional[str] = None):
        """
        Update a single embedding

        Args:
            id: Document ID
            embedding: New embedding vector
            metadata: Updated metadata
            document: Updated document text
        """
        # Convert numpy array to list if needed
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()

        self.collection.update(
            ids=[id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[document] if document else None
        )

    def get_stats(self) -> Dict:
        """
        Get statistics about the collection

        Returns:
            Dictionary with stats
        """
        total = self.collection.count()

        # Sample some documents to get language distribution
        if total > 0:
            sample_size = min(1000, total)
            sample = self.collection.get(limit=sample_size)

            languages = {}
            node_types = {}

            for meta in sample['metadatas']:
                lang = meta.get('language', 'unknown')
                languages[lang] = languages.get(lang, 0) + 1

                ntype = meta.get('node_type', 'unknown')
                node_types[ntype] = node_types.get(ntype, 0) + 1

            return {
                'total_documents': total,
                'languages': languages,
                'node_types': node_types,
                'sample_size': sample_size
            }
        else:
            return {
                'total_documents': 0,
                'languages': {},
                'node_types': {}
            }

    def search_by_metadata(self, filters: Dict, limit: int = 100) -> Dict:
        """
        Search documents by metadata filters

        Args:
            filters: Metadata filters (e.g., {"language": "python", "node_type": "function"})
            limit: Maximum results

        Returns:
            Matching documents
        """
        return self.collection.get(
            where=filters,
            limit=limit
        )

    def clear_collection(self):
        """Clear all documents from collection (keeps collection structure)"""
        # Get all IDs
        all_docs = self.collection.get()
        if all_docs['ids']:
            self.collection.delete(ids=all_docs['ids'])
            print(f"🗑️  Cleared all documents from '{self.collection_name}'")
        else:
            print(f"ℹ️  Collection '{self.collection_name}' is already empty")
