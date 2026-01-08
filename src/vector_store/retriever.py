"""
Hybrid retriever combining vector search + semantic tree

This is the KEY component that makes RAG powerful:
1. Vector search finds semantically similar code
2. Semantic tree expands context with callers/callees
3. Result: Rich, connected code context for LLM
"""
from typing import List, Dict, Optional, Set
import os


class HybridRetriever:
    """
    Combine vector search with semantic tree for rich context retrieval

    Flow:
    User Question
        ↓
    [Vector Search] → Top-K similar functions
        ↓
    [Semantic Expansion] → Add callers, callees, tests
        ↓
    [Context Assembly] → Format for LLM
    """

    def __init__(
        self,
        vector_store,
        semantic_tree: Dict,
        repository_path: str,
        embedding_generator
    ):
        """
        Initialize hybrid retriever

        Args:
            vector_store: ChromaVectorStore instance
            semantic_tree: Dict with 'nodes' and 'node_map'
            repository_path: Path to repository
            embedding_generator: EmbeddingGenerator instance
        """
        self.vector_store = vector_store
        self.nodes = semantic_tree['nodes']
        self.node_map = semantic_tree['node_map']
        self.repository_path = repository_path
        self.embedding_generator = embedding_generator

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
        expand_context: bool = True,
        max_context_items: int = 15,
        language_filter: Optional[str] = None,
        min_similarity: float = 0.25
    ) -> Dict:
        """
        Retrieve relevant code for a question

        Args:
            question: User's natural language question
            top_k: Number of initial vector search results
            expand_context: Whether to expand with semantic tree
            max_context_items: Maximum total context items to return
            language_filter: Filter by language (e.g., "python")
            min_similarity: Minimum similarity score (0-1) to consider relevant

        Returns:
            Dictionary with retrieved code and metadata
        """
        print(f"\n🔍 Retrieving context for: '{question}'")

        # Step 1: Vector search
        print(f"   📊 Step 1: Vector search (top-{top_k})...")
        vector_results = self._vector_search(question, top_k, language_filter)

        # Filter by minimum similarity (distance = 1 - similarity for cosine)
        filtered_results = []
        for result in vector_results:
            similarity = 1 - result['distance']
            if similarity >= min_similarity:
                filtered_results.append(result)

        vector_results = filtered_results

        if not vector_results:
            print("   ⚠️  No relevant results found (all below similarity threshold)!")
            return {
                'question': question,
                'results': [],
                'total_items': 0,
                'message': f"No code found related to '{question}'. This question may be outside the scope of this codebase."
            }

        print(f"   ✅ Found {len(vector_results)} vector matches")

        # Step 2: Expand with semantic tree
        if expand_context:
            print(f"   🌳 Step 2: Expanding with semantic tree...")
            expanded_results = self._expand_with_semantic_tree(
                vector_results,
                max_items=max_context_items
            )
            print(f"   ✅ Expanded to {len(expanded_results)} total items")
        else:
            expanded_results = vector_results

        # Step 3: Read source code
        print(f"   📖 Step 3: Reading source code...")
        enriched_results = self._enrich_with_source_code(expanded_results)

        print(f"   ✅ Retrieved {len(enriched_results)} code chunks\n")

        return {
            'question': question,
            'results': enriched_results,
            'total_items': len(enriched_results)
        }

    def _vector_search(
        self,
        question: str,
        top_k: int,
        language_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Perform vector similarity search

        Args:
            question: User question
            top_k: Number of results
            language_filter: Optional language filter

        Returns:
            List of result dictionaries
        """
        # Generate embedding for question
        question_embedding = self.embedding_generator.embed_single(question)

        # Build metadata filter
        where_filter = None
        if language_filter:
            where_filter = {"language": language_filter}

        # Search
        results = self.vector_store.query(
            query_embedding=question_embedding,
            n_results=top_k,
            where=where_filter
        )

        # Convert to our format
        result_list = []
        if results['ids'] and len(results['ids']) > 0:
            for i, result_id in enumerate(results['ids'][0]):
                result_list.append({
                    'id': result_id,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'source': 'vector_search',
                    'rank': i + 1
                })

        return result_list

    def _expand_with_semantic_tree(
        self,
        vector_results: List[Dict],
        max_items: int = 15
    ) -> List[Dict]:
        """
        Expand vector results with semantic tree context

        For each result:
        - Add immediate callers (who uses this?)
        - Add immediate callees (what does this use?)
        - Add related tests

        Args:
            vector_results: Results from vector search
            max_items: Maximum total items to return

        Returns:
            Expanded results list
        """
        expanded = []
        seen_ids = set()

        # First, add all vector results (they're most relevant)
        for result in vector_results:
            if len(expanded) >= max_items:
                break

            result_id = result['id']
            if result_id not in seen_ids:
                expanded.append(result)
                seen_ids.add(result_id)

        # Then, expand each result with semantic context
        for result in vector_results[:3]:  # Expand top 3 results only
            if len(expanded) >= max_items:
                break

            # Get the node
            node_id = result['metadata']['qualified_name']
            filepath = result['metadata']['filepath']
            full_path = f"{filepath}::{node_id}"

            if full_path not in self.node_map:
                continue

            node = self.node_map[full_path]

            # Add callers (breaking change risk)
            for caller_path in node.called_by[:2]:  # Top 2 callers
                if len(expanded) >= max_items:
                    break

                if caller_path in self.node_map and caller_path not in seen_ids:
                    caller_node = self.node_map[caller_path]
                    expanded.append({
                        'id': caller_path,
                        'metadata': {
                            'qualified_name': caller_node.qualified_name,
                            'filepath': caller_node.filepath,
                            'start_line': caller_node.start_line,
                            'end_line': caller_node.end_line,
                            'node_type': caller_node.node_type,
                            'language': caller_node.language,
                        },
                        'source': 'semantic_caller',
                        'related_to': result_id
                    })
                    seen_ids.add(caller_path)

            # Add callees (dependencies)
            for callee_path in node.calls[:2]:  # Top 2 callees
                if len(expanded) >= max_items:
                    break

                if callee_path in self.node_map and callee_path not in seen_ids:
                    callee_node = self.node_map[callee_path]
                    expanded.append({
                        'id': callee_path,
                        'metadata': {
                            'qualified_name': callee_node.qualified_name,
                            'filepath': callee_node.filepath,
                            'start_line': callee_node.start_line,
                            'end_line': callee_node.end_line,
                            'node_type': callee_node.node_type,
                            'language': callee_node.language,
                        },
                        'source': 'semantic_callee',
                        'related_to': result_id
                    })
                    seen_ids.add(callee_path)

        return expanded

    def _enrich_with_source_code(self, results: List[Dict]) -> List[Dict]:
        """
        Add actual source code to results

        Args:
            results: Results with metadata

        Returns:
            Results enriched with source code
        """
        enriched = []

        for result in results:
            metadata = result['metadata']

            # Read source code
            code = self._read_code(
                metadata['filepath'],
                metadata['start_line'],
                metadata['end_line']
            )

            enriched.append({
                **result,
                'code': code,
                'location': f"{metadata['filepath']}:{metadata['start_line']}-{metadata['end_line']}"
            })

        return enriched

    def _read_code(self, filepath: str, start_line: int, end_line: int) -> str:
        """
        Read code from file

        Args:
            filepath: Relative file path
            start_line: Start line (1-indexed)
            end_line: End line (1-indexed)

        Returns:
            Source code string
        """
        try:
            full_path = os.path.join(self.repository_path, filepath)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                code_lines = lines[start_line - 1:end_line]
                return ''.join(code_lines)
        except Exception as e:
            return f"# Error reading code: {e}"

    def format_for_llm(self, retrieval_result: Dict, max_tokens: int = 8000) -> str:
        """
        Format retrieved context for LLM

        Args:
            retrieval_result: Result from retrieve()
            max_tokens: Maximum tokens to use

        Returns:
            Formatted context string
        """
        question = retrieval_result['question']
        results = retrieval_result['results']

        parts = [
            f"# Question: {question}",
            "",
            "# Relevant Code Context",
            ""
        ]

        tokens_used = len(' '.join(parts)) // 4  # Rough estimate

        for i, result in enumerate(results, 1):
            if tokens_used >= max_tokens:
                parts.append("\n... (additional context truncated due to token limit)")
                break

            metadata = result['metadata']
            code = result.get('code', '')
            source = result.get('source', 'unknown')

            # Add section header
            header = f"\n## {i}. {metadata['qualified_name']}"
            if source != 'vector_search':
                header += f" (via {source})"

            parts.append(header)
            parts.append(f"**Location**: `{result['location']}`")
            parts.append(f"**Type**: {metadata['node_type']}")

            if 'distance' in result:
                similarity = 1 - result['distance']
                parts.append(f"**Relevance**: {similarity:.2%}")

            parts.append(f"\n```{metadata['language']}\n{code}\n```")

            # Estimate tokens
            tokens_used += len(code) // 4

        return '\n'.join(parts)
