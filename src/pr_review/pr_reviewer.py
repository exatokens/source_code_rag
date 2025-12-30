"""
PR Reviewer - Orchestrates the entire PR review process
Implements README Step 3: Dynamic Context Retrieval
"""
from typing import Optional, List, Dict
from src.parsers.repository_scanner import RepositoryScanner
from src.utils.call_graph_builder import CallGraphBuilder
from src.github.pr_fetcher import PRFetcher
from src.diff_parser.diff_parser import DiffParser
from src.context_retrieval.context_builder import ContextBuilder
from src.llm_integration.llm_client import LLMClient, LLMConfig


class PRReviewer:
    """
    Complete PR review system

    Workflow:
    1. Fetch PR diff from GitHub
    2. Parse diff to find changed files/functions
    3. Map changes to semantic tree nodes
    4. Build context (Level 1, 2, 3) for each changed function
    5. Send to LLM for review
    """

    def __init__(
        self,
        repository_path: str,
        llm_config: LLMConfig,
        github_token: Optional[str] = None
    ):
        """
        Initialize PR Reviewer

        Args:
            repository_path: Path to local repository
            llm_config: LLM configuration
            github_token: Optional GitHub token
        """
        self.repository_path = repository_path
        self.llm_config = llm_config
        self.github_token = github_token

        # Initialize components
        self.pr_fetcher = PRFetcher(github_token)
        self.llm_client = LLMClient(llm_config)

        # Will be initialized during review
        self.scanner = None
        self.nodes = None
        self.node_map = None
        self.context_builder = None

    def scan_repository(self):
        """Scan repository and build semantic tree"""
        print(f"📦 Scanning repository: {self.repository_path}")

        self.scanner = RepositoryScanner()
        self.nodes = self.scanner.scan_repository(self.repository_path)

        print("🔗 Building call graph...")
        CallGraphBuilder.build_call_graph(self.nodes, self.scanner.node_map)

        self.node_map = self.scanner.node_map
        self.context_builder = ContextBuilder(
            self.nodes,
            self.node_map,
            self.repository_path
        )

        stats = self.scanner.get_statistics()
        print(f"✓ Scanned {stats['total_files']} files")
        print(f"✓ Found {stats['total_functions'] + stats['total_methods']} functions/methods")
        print()

    def review_pr(self, pr_url: str, max_tokens: int = 8000) -> Dict:
        """
        Review a GitHub Pull Request

        Args:
            pr_url: GitHub PR URL
            max_tokens: Max tokens for context

        Returns:
            Review results dict
        """
        # Ensure repository is scanned
        if not self.nodes:
            self.scan_repository()

        print(f"📥 Fetching PR: {pr_url}")

        # Fetch PR metadata and diff
        metadata = self.pr_fetcher.fetch_pr_metadata(pr_url)
        diff_content = self.pr_fetcher.fetch_pr_diff(pr_url)

        print(f"✓ PR #{metadata['number']}: {metadata['title']}")
        print(f"✓ Author: {metadata['user']['login']}")
        print()

        # Parse diff
        print("📝 Parsing diff...")
        file_changes = DiffParser.parse_diff(diff_content)
        print(f"✓ Found {len(file_changes)} changed file(s)")
        print()

        # Review each changed file
        reviews = []
        for file_change in file_changes:
            print(f"🔍 Analyzing: {file_change.filepath}")

            # Get nodes for this file
            file_nodes = [n for n in self.nodes if n.filepath == file_change.filepath]

            # Find changed functions
            changed_nodes = DiffParser.get_changed_functions(file_change, file_nodes)

            if not changed_nodes:
                print(f"  ℹ️  No functions/methods directly modified")
                # Still review the file-level changes
                review = self._review_file_change(file_change, diff_content, max_tokens)
                reviews.append({
                    'file': file_change.filepath,
                    'changed_nodes': [],
                    'review': review
                })
            else:
                print(f"  ✓ Found {len(changed_nodes)} modified function(s)/method(s)")

                # Print changed function names
                for node in changed_nodes:
                    print(f"    → {node.qualified_name}")

                print(f"\n  🤖 Sending to LLM for review...")

                # Review each changed function
                for i, node in enumerate(changed_nodes, 1):
                    print(f"\n  ━━━ Review {i}/{len(changed_nodes)} ━━━")
                    review = self._review_changed_node(
                        node,
                        file_change,
                        diff_content,
                        max_tokens
                    )

                    reviews.append({
                        'file': file_change.filepath,
                        'node': node.full_path,
                        'review': review
                    })

            print()

        return {
            'pr_url': pr_url,
            'pr_number': metadata['number'],
            'pr_title': metadata['title'],
            'author': metadata['user']['login'],
            'files_changed': len(file_changes),
            'reviews': reviews
        }

    def _review_file_change(
        self,
        file_change,
        diff_content: str,
        max_tokens: int
    ) -> str:
        """Review file-level changes when no specific function is identified"""
        context = f"""
## File Changes

**File**: {file_change.filepath}
**Status**: {file_change.status}
**Lines Added**: {len(file_change.added_lines)}
**Lines Removed**: {len(file_change.removed_lines)}

### Added Lines:
"""
        for line_num, content in file_change.added_lines[:20]:
            context += f"\n{line_num}: {content}"

        # Get relevant diff section
        file_diff = self._extract_file_diff(diff_content, file_change.filepath)

        return self.llm_client.review_code_change(context, file_diff)

    def _review_changed_node(
        self,
        node,
        file_change,
        diff_content: str,
        max_tokens: int
    ) -> str:
        """Review a specific changed function/method"""
        # Build rich context using ContextBuilder (README Step 3 & 5)
        context = self.context_builder.build_review_context(node, max_tokens)

        # Get relevant diff section
        file_diff = self._extract_file_diff(diff_content, file_change.filepath)

        # Send to LLM for review
        return self.llm_client.review_code_change(context, file_diff)

    def _extract_file_diff(self, diff_content: str, filepath: str) -> str:
        """Extract diff section for a specific file"""
        lines = diff_content.split('\n')
        file_diff = []
        in_file = False

        for line in lines:
            if line.startswith('diff --git') and filepath in line:
                in_file = True
            elif line.startswith('diff --git') and in_file:
                break

            if in_file:
                file_diff.append(line)

        return '\n'.join(file_diff)

    def answer_question(self, question: str, about_function: Optional[str] = None) -> str:
        """
        Answer a question about the codebase

        Args:
            question: User's question
            about_function: Optional function name to focus on

        Returns:
            LLM answer
        """
        if not self.nodes:
            self.scan_repository()

        # Build context
        if about_function:
            # Find the function
            from src.utils.node_search import NodeSearch
            results = NodeSearch.search_function(self.nodes, about_function)

            if not results:
                return f"Could not find function '{about_function}' in the codebase."

            # Build context for the first match
            node = results[0]
            context = self.context_builder.build_review_context(node, max_tokens=4000)
        else:
            # General question - provide repository summary
            stats = self.scanner.get_statistics()
            context = f"""
# Repository Summary

- Total Files: {stats['total_files']}
- Total Classes: {stats['total_classes']}
- Total Functions: {stats['total_functions']}
- Total Methods: {stats['total_methods']}

Languages:
"""
            for lang, counts in stats['by_language'].items():
                context += f"\n- {lang.upper()}: {counts['functions'] + counts['methods']} functions/methods"

        return self.llm_client.answer_question(question, context)

    def print_review_summary(self, review_result: Dict):
        """Print a formatted summary of the review"""
        print("\n" + "="*80)
        print(f"PR REVIEW SUMMARY")
        print("="*80)
        print(f"PR: #{review_result['pr_number']} - {review_result['pr_title']}")
        print(f"Author: {review_result['author']}")
        print(f"Files Changed: {review_result['files_changed']}")
        print("="*80)
        print()

        for i, review in enumerate(review_result['reviews'], 1):
            print(f"\n{'─'*80}")
            print(f"Review {i}/{len(review_result['reviews'])}")
            print(f"{'─'*80}")
            print(f"File: {review['file']}")
            if 'node' in review:
                print(f"Function: {review['node']}")
            print()
            print(review['review'])
            print()
