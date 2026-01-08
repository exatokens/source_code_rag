"""
Index entire repository for RAG

Workflow:
1. Parse repo → Semantic tree (using existing code)
2. Filter nodes for embedding (using ChunkStrategy)
3. Generate embeddings (using EmbeddingGenerator)
4. Store in ChromaDB (using ChromaVectorStore)
"""
import os
from typing import List, Dict, Optional
from pathlib import Path


class RepositoryIndexer:
    """
    Index a GitHub repository for semantic search

    Combines:
    - Semantic tree builder (existing)
    - Embedding generation (new)
    - Vector storage (new)
    """

    def __init__(
        self,
        repository_path: str,
        collection_name: Optional[str] = None,
        persist_directory: str = "./chroma_db"
    ):
        """
        Initialize repository indexer

        Args:
            repository_path: Path to local repository
            collection_name: Name for the vector collection (default: repo name)
            persist_directory: Where to store ChromaDB data
        """
        self.repository_path = os.path.abspath(repository_path)

        # Auto-generate collection name from repo
        if collection_name is None:
            repo_name = os.path.basename(self.repository_path)
            collection_name = f"code_{repo_name}".lower().replace('-', '_')

        self.collection_name = collection_name
        self.persist_directory = persist_directory

        # Initialize components (lazy loading)
        self.semantic_tree = None
        self.embedding_generator = None
        self.vector_store = None
        self.preprocessor = None
        self.chunk_strategy = None

        print(f"📁 Repository: {self.repository_path}")
        print(f"🏷️  Collection: {self.collection_name}")

    def index(
        self,
        granularity: str = "function",
        force_rebuild: bool = False,
        show_progress: bool = True
    ) -> Dict:
        """
        Index the entire repository

        Args:
            granularity: Chunking granularity ("function", "class", "file")
            force_rebuild: Clear existing index and rebuild
            show_progress: Show progress information

        Returns:
            Dictionary with indexing stats
        """
        from semantic_tree_builder import MultiLanguageScanner
        from src.embeddings import EmbeddingGenerator, CodePreprocessor, ChunkStrategy
        from src.vector_store import ChromaVectorStore

        print("\n" + "="*60)
        print("🚀 INDEXING REPOSITORY")
        print("="*60)

        # Step 1: Build semantic tree
        print("\n📊 Step 1/4: Building semantic tree...")
        scanner = MultiLanguageScanner()
        nodes = scanner.scan_repository(self.repository_path)
        node_map = scanner.node_map
        self.semantic_tree = {'nodes': nodes, 'node_map': node_map}

        print(f"   ✅ Parsed {len(nodes)} semantic nodes")

        # Step 2: Filter nodes for embedding
        print(f"\n📋 Step 2/4: Filtering nodes (granularity: {granularity})...")
        self.chunk_strategy = ChunkStrategy(granularity=granularity)
        nodes_to_embed = self.chunk_strategy.filter_nodes_for_embedding(nodes)

        if not nodes_to_embed:
            print("   ⚠️  No nodes to embed! Check your filters.")
            return {'success': False, 'total_embedded': 0}

        # Step 3: Generate embeddings
        print(f"\n🔮 Step 3/4: Generating embeddings...")
        self.embedding_generator = EmbeddingGenerator()
        self.preprocessor = CodePreprocessor()

        # Prepare texts for embedding
        texts_to_embed = []
        metadatas = []

        for node in nodes_to_embed:
            # Get code text
            code_text = self._read_node_code(node)

            # Prepare rich text for embedding
            rich_text = self.preprocessor.prepare_for_embedding(node, code_text)
            texts_to_embed.append(rich_text)

            # Prepare metadata
            metadata = {
                'qualified_name': node.qualified_name,
                'filepath': node.filepath,
                'start_line': node.start_line,
                'end_line': node.end_line,
                'node_type': node.node_type,
                'language': node.language,
                'parent_class': getattr(node, 'parent_class', None) or '',
                'parameters': ','.join(getattr(node, 'parameters', []) or []),
                'calls_count': len(getattr(node, 'calls', []) or []),
                'called_by_count': len(getattr(node, 'called_by', []) or [])
            }
            metadatas.append(metadata)

        # Generate embeddings in batch
        embeddings = self.embedding_generator.embed_batch(
            texts_to_embed,
            batch_size=32,
            show_progress=show_progress
        )

        print(f"   ✅ Generated {len(embeddings)} embeddings")

        # Step 4: Store in vector database
        print(f"\n💾 Step 4/4: Storing in ChromaDB...")
        self.vector_store = ChromaVectorStore(
            persist_directory=self.persist_directory,
            collection_name=self.collection_name
        )

        # Clear if force rebuild
        if force_rebuild:
            print("   🗑️  Clearing existing collection...")
            self.vector_store.clear_collection()

        # Add embeddings
        self.vector_store.add_embeddings(
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts_to_embed  # Store the rich text for reference
        )

        # Get stats
        stats = self.vector_store.get_stats()

        print("\n" + "="*60)
        print("✅ INDEXING COMPLETE")
        print("="*60)
        print(f"📊 Total documents: {stats['total_documents']}")
        print(f"🌐 Languages: {dict(stats['languages'])}")
        print(f"📦 Node types: {dict(stats['node_types'])}")
        print("="*60 + "\n")

        return {
            'success': True,
            'total_embedded': len(embeddings),
            'stats': stats,
            'collection_name': self.collection_name
        }

    def _read_node_code(self, node: object) -> str:
        """
        Read source code for a node

        Args:
            node: SemanticNode object

        Returns:
            Source code text
        """
        try:
            filepath = os.path.join(self.repository_path, node.filepath)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Extract node's lines (1-indexed)
                code_lines = lines[node.start_line - 1:node.end_line]
                return ''.join(code_lines)
        except Exception as e:
            print(f"   ⚠️  Could not read {node.filepath}: {e}")
            return ""

    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the indexed collection

        Returns:
            Stats dictionary
        """
        if self.vector_store is None:
            from src.vector_store import ChromaVectorStore
            self.vector_store = ChromaVectorStore(
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )

        return self.vector_store.get_stats()

    def delete_index(self):
        """Delete the entire index (use with caution!)"""
        if self.vector_store is None:
            from src.vector_store import ChromaVectorStore
            self.vector_store = ChromaVectorStore(
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )

        self.vector_store.delete_collection()
        print(f"🗑️  Deleted index for '{self.collection_name}'")
