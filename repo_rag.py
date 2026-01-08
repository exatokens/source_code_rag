"""
Repository RAG - Main interface for querying code repositories

Usage:
    # Index a repository
    python repo_rag.py index /path/to/repo

    # Query the repository
    python repo_rag.py query "How does authentication work?"

    # Interactive mode
    python repo_rag.py interactive /path/to/repo
"""
import sys
import os
from typing import Optional, Dict


class RepoRAG:
    """
    Main RAG interface for GitHub repositories

    Combines:
    - Repository indexing (semantic tree + embeddings)
    - Hybrid retrieval (vector search + semantic expansion)
    - LLM integration (answer generation)
    """

    def __init__(
        self,
        repository_path: str,
        collection_name: Optional[str] = None,
        persist_directory: str = "./chroma_db"
    ):
        """
        Initialize RepoRAG

        Args:
            repository_path: Path to local repository
            collection_name: Collection name (auto-generated if None)
            persist_directory: Where to store vector database
        """
        self.repository_path = os.path.abspath(repository_path)
        self.persist_directory = persist_directory

        if collection_name is None:
            repo_name = os.path.basename(self.repository_path)
            collection_name = f"code_{repo_name}".lower().replace('-', '_')

        self.collection_name = collection_name

        # Components (lazy loaded)
        self.indexer = None
        self.vector_store = None
        self.embedding_generator = None
        self.retriever = None
        self.llm_client = None
        self.semantic_tree = None

        print(f"\n{'='*60}")
        print(f"🔍 Repository RAG System")
        print(f"{'='*60}")
        print(f"📁 Repository: {self.repository_path}")
        print(f"🏷️  Collection: {self.collection_name}")
        print(f"💾 Database: {self.persist_directory}")
        print(f"{'='*60}\n")

    def index(self, granularity: str = "function", force_rebuild: bool = False):
        """
        Index the repository

        Args:
            granularity: Chunking strategy ("function", "class", "file")
            force_rebuild: Rebuild index from scratch
        """
        from src.vector_store.indexer import RepositoryIndexer

        self.indexer = RepositoryIndexer(
            repository_path=self.repository_path,
            collection_name=self.collection_name,
            persist_directory=self.persist_directory
        )

        result = self.indexer.index(
            granularity=granularity,
            force_rebuild=force_rebuild,
            show_progress=True
        )

        if result['success']:
            # Store semantic tree for later use
            self.semantic_tree = self.indexer.semantic_tree

        return result

    def query(
        self,
        question: str,
        top_k: int = 5,
        use_llm: bool = True,
        language_filter: Optional[str] = None
    ) -> Dict:
        """
        Query the repository

        Args:
            question: Natural language question
            top_k: Number of initial results
            use_llm: Whether to use LLM for answer generation
            language_filter: Filter by language

        Returns:
            Query result with answer and context
        """
        # Initialize components if needed
        self._ensure_components_loaded()

        print(f"\n{'='*60}")
        print(f"❓ Question: {question}")
        print(f"{'='*60}")

        # Retrieve relevant code
        retrieval_result = self.retriever.retrieve(
            question=question,
            top_k=top_k,
            expand_context=True,
            max_context_items=15,
            language_filter=language_filter
        )

        if retrieval_result['total_items'] == 0:
            message = retrieval_result.get('message', "No relevant code found.")
            print(f"\n⚠️  {message}")
            return {
                'question': question,
                'answer': f"I couldn't find any relevant code for this question.\n\n{message}\n\nThis codebase appears to be a Streamlit application with GitHub migration features, authentication, and data management utilities. Please ask questions related to this codebase.",
                'context': []
            }

        # Format context for LLM
        formatted_context = self.retriever.format_for_llm(retrieval_result)

        # Print retrieved context
        print("\n📦 Retrieved Context:")
        for i, result in enumerate(retrieval_result['results'][:5], 1):
            meta = result['metadata']
            source = result.get('source', 'vector_search')
            print(f"   {i}. {meta['qualified_name']} ({meta['filepath']}) [{source}]")

        # Generate answer with LLM if requested
        if use_llm:
            print(f"\n🤖 Generating answer with LLM...")
            answer = self._generate_answer(question, formatted_context)
        else:
            answer = "LLM disabled. See context below."

        print(f"\n{'='*60}")
        print(f"✅ Answer Generated")
        print(f"{'='*60}\n")

        return {
            'question': question,
            'answer': answer,
            'context': retrieval_result['results'],
            'formatted_context': formatted_context
        }

    def _ensure_components_loaded(self):
        """Ensure all components are initialized"""
        if self.vector_store is None:
            from src.vector_store import ChromaVectorStore
            self.vector_store = ChromaVectorStore(
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )

        if self.embedding_generator is None:
            from src.embeddings import EmbeddingGenerator
            self.embedding_generator = EmbeddingGenerator()

        if self.semantic_tree is None:
            # Need to rebuild semantic tree
            from semantic_tree_builder import MultiLanguageScanner
            print("🔄 Building semantic tree...")
            scanner = MultiLanguageScanner()
            nodes = scanner.scan_repository(self.repository_path)
            node_map = scanner.node_map
            self.semantic_tree = {'nodes': nodes, 'node_map': node_map}

        if self.retriever is None:
            from src.vector_store import HybridRetriever
            self.retriever = HybridRetriever(
                vector_store=self.vector_store,
                semantic_tree=self.semantic_tree,
                repository_path=self.repository_path,
                embedding_generator=self.embedding_generator
            )

    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using LLM

        Args:
            question: User question
            context: Retrieved code context

        Returns:
            LLM-generated answer
        """
        if self.llm_client is None:
            from src.llm_integration.llm_client import LLMClient, LLMConfig
            import os
            from dotenv import load_dotenv

            load_dotenv()

            # Try to use Ollama first (local), fallback to Groq
            ollama_available = os.path.exists("/usr/local/bin/ollama") or os.getenv("USE_OLLAMA") == "true"

            if ollama_available:
                # Use local Ollama (free, private, offline)
                config = LLMConfig(
                    provider="local",
                    model="llama3",  # or "qwen2:7b", "mistral", "codellama"
                    api_base="http://localhost:11434",
                    temperature=0.7,
                    max_tokens=2000
                )
            else:
                # Fallback to Groq
                config = LLMConfig(
                    provider="groq",
                    model="llama-3.1-70b-versatile",
                    api_key=os.getenv("GROQ_API_KEY"),
                    temperature=0.7,
                    max_tokens=2000
                )

            self.llm_client = LLMClient(config)

        try:
            # Use the answer_question method from LLMClient
            response = self.llm_client.answer_question(question, context)
            return response
        except Exception as e:
            return f"Error generating answer: {e}\n\nPlease review the context above."

    def interactive(self):
        """Interactive query mode"""
        print("\n🎯 Interactive Mode")
        print("Type your questions (or 'quit' to exit)\n")

        while True:
            try:
                question = input("\n❓ Your question: ").strip()

                if question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break

                if not question:
                    continue

                # Query
                result = self.query(question, use_llm=True)

                # Print answer
                print(f"\n💡 Answer:\n{result['answer']}\n")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")

    def get_stats(self) -> Dict:
        """Get indexing statistics"""
        if self.vector_store is None:
            from src.vector_store import ChromaVectorStore
            self.vector_store = ChromaVectorStore(
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )

        return self.vector_store.get_stats()


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Repository RAG System")
    parser.add_argument(
        'command',
        choices=['index', 'query', 'interactive', 'stats'],
        help='Command to execute'
    )
    parser.add_argument(
        'path_or_query',
        nargs='?',
        help='Repository path (for index/interactive) or query (for query)'
    )
    parser.add_argument(
        '--granularity',
        default='function',
        choices=['function', 'class', 'file'],
        help='Chunking granularity for indexing'
    )
    parser.add_argument(
        '--force-rebuild',
        action='store_true',
        help='Force rebuild index'
    )
    parser.add_argument(
        '--no-llm',
        action='store_true',
        help='Disable LLM answer generation'
    )
    parser.add_argument(
        '--language',
        help='Filter by programming language'
    )
    parser.add_argument(
        '--repo-path',
        help='Repository path (for query command)'
    )

    args = parser.parse_args()

    if args.command == 'index':
        if not args.path_or_query:
            print("❌ Error: Please provide repository path")
            sys.exit(1)

        rag = RepoRAG(args.path_or_query)
        rag.index(granularity=args.granularity, force_rebuild=args.force_rebuild)

    elif args.command == 'query':
        if not args.path_or_query:
            print("❌ Error: Please provide a query")
            sys.exit(1)

        repo_path = args.repo_path or '.'
        rag = RepoRAG(repo_path)
        result = rag.query(
            args.path_or_query,
            use_llm=not args.no_llm,
            language_filter=args.language
        )

        print(f"\n💡 Answer:\n{result['answer']}\n")

    elif args.command == 'interactive':
        if not args.path_or_query:
            print("❌ Error: Please provide repository path")
            sys.exit(1)

        rag = RepoRAG(args.path_or_query)

        # Check if index exists
        stats = rag.get_stats()
        if stats['total_documents'] == 0:
            print("\n⚠️  No index found. Indexing repository first...")
            rag.index()

        rag.interactive()

    elif args.command == 'stats':
        repo_path = args.path_or_query or '.'
        rag = RepoRAG(repo_path)
        stats = rag.get_stats()

        print(f"\n📊 Index Statistics:")
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   Languages: {stats['languages']}")
        print(f"   Node types: {stats['node_types']}\n")


if __name__ == '__main__':
    main()
