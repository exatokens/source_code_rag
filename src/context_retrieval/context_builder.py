"""
Build context for PR review following README Step 3 & Step 5
Implements 3-level context retrieval with smart token management
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional


class ContextLevel(Enum):
    """Context priority levels from README"""
    DIRECT = 1  # Level 1: Changed code + immediate callers/callees
    EXTENDED = 2  # Level 2: Parent classes, tests
    PERIPHERAL = 3  # Level 3: Metadata only


@dataclass
class CodeContext:
    """Represents code context for a changed function"""
    # Level 1: Direct context (always include)
    changed_code: str
    changed_node: object  # SemanticNode
    immediate_callers: List[Dict]  # [{node, code}]
    immediate_callees: List[Dict]  # [{node, code}]

    # Level 2: Extended context
    parent_class: Optional[Dict]  # {node, code}
    related_tests: List[Dict]  # [{node, code}]

    # Level 3: Peripheral context (metadata)
    file_imports: List[str]
    constants_used: List[str]
    all_callers_count: int
    test_coverage: Optional[float]


class ContextBuilder:
    """
    Build smart context for PR review
    Following README.md Step 3 & Step 5
    """

    def __init__(self, nodes: list, node_map: dict, repository_path: str):
        """
        Initialize context builder

        Args:
            nodes: List of all SemanticNode objects
            node_map: Dict mapping full_path -> SemanticNode
            repository_path: Path to the repository
        """
        self.nodes = nodes
        self.node_map = node_map
        self.repository_path = repository_path

    def build_context_for_changes(
        self,
        changed_nodes: list,
        max_tokens: int = 8000,
        include_tests: bool = True
    ) -> List[CodeContext]:
        """
        Build context for changed nodes

        Args:
            changed_nodes: List of SemanticNode objects that changed
            max_tokens: Maximum token budget
            include_tests: Whether to include test files

        Returns:
            List of CodeContext objects
        """
        contexts = []

        for node in changed_nodes:
            context = self._build_single_context(node, max_tokens, include_tests)
            contexts.append(context)

        return contexts

    def _build_single_context(
        self,
        changed_node: object,
        max_tokens: int,
        include_tests: bool
    ) -> CodeContext:
        """
        Build context for a single changed node
        Following README Step 5 prioritization
        """
        # Level 1: Direct context
        changed_code = self._get_node_code(changed_node)
        immediate_callers = self._get_immediate_callers(changed_node)
        immediate_callees = self._get_immediate_callees(changed_node)

        # Level 2: Extended context
        parent_class = self._get_parent_class(changed_node)
        related_tests = self._get_related_tests(changed_node) if include_tests else []

        # Level 3: Peripheral context (metadata)
        file_imports = self._get_file_imports(changed_node)
        constants_used = []  # TODO: Implement constant detection
        all_callers_count = len(changed_node.called_by)
        test_coverage = None  # TODO: Implement test coverage calculation

        return CodeContext(
            changed_code=changed_code,
            changed_node=changed_node,
            immediate_callers=immediate_callers,
            immediate_callees=immediate_callees,
            parent_class=parent_class,
            related_tests=related_tests,
            file_imports=file_imports,
            constants_used=constants_used,
            all_callers_count=all_callers_count,
            test_coverage=test_coverage
        )

    def build_review_context(
        self,
        changed_node: object,
        max_tokens: int = 8000,
        verbose: bool = True
    ) -> str:
        """
        Build formatted context string for LLM review
        Implements README Step 5: Context Window Management

        Args:
            changed_node: SemanticNode that was modified
            max_tokens: Maximum token budget
            verbose: Print context retrieval details to console

        Returns:
            Formatted context string
        """
        if verbose:
            print(f"\n    📊 Building context for: {changed_node.qualified_name}")
            print(f"    📦 Token budget: {max_tokens}")
            print(f"\n    🔍 Level 1 - Direct Context:")

        context_parts = []
        tokens_used = 0

        # Priority 1: The changed code itself (always include)
        changed_code = self._get_node_code(changed_node)
        context_parts.append(f"## Changed Code\n\n```python\n{changed_code}\n```\n")
        tokens_used += self._estimate_tokens(changed_code)

        if verbose:
            print(f"      ✓ Changed code: {self._estimate_tokens(changed_code)} tokens")

        # Priority 2: Direct callers (breaking change risk)
        callers = self._get_immediate_callers(changed_node)
        callers_added = 0
        if tokens_used < max_tokens * 0.4 and callers:
            context_parts.append("\n## Functions That Call This (May Break)\n")
            for caller_info in callers:
                if tokens_used < max_tokens * 0.4:
                    caller_code = caller_info['code']
                    context_parts.append(f"\n### {caller_info['node'].full_path}\n```python\n{caller_code}\n```\n")
                    tokens_used += self._estimate_tokens(caller_code)
                    callers_added += 1

        if verbose:
            print(f"      ✓ Callers: {callers_added}/{len(callers)} included ({len(changed_node.called_by)} total)")

        # Priority 3: Direct callees (understanding dependencies)
        callees = self._get_immediate_callees(changed_node)
        callees_added = 0
        if tokens_used < max_tokens * 0.6 and callees:
            context_parts.append("\n## Functions This Calls (Dependencies)\n")
            for callee_info in callees:
                if tokens_used < max_tokens * 0.6:
                    callee_code = callee_info['code']
                    context_parts.append(f"\n### {callee_info['node'].full_path}\n```python\n{callee_code}\n```\n")
                    tokens_used += self._estimate_tokens(callee_code)
                    callees_added += 1

        if verbose:
            print(f"      ✓ Callees: {callees_added}/{len(callees)} included ({len(changed_node.calls)} total)")
            print(f"\n    🔍 Level 2 - Extended Context:")

        # Priority 4: Tests (expected behavior)
        tests = self._get_related_tests(changed_node)
        tests_added = 0
        if tokens_used < max_tokens * 0.8 and tests:
            context_parts.append("\n## Related Tests\n")
            for test_info in tests:
                if tokens_used < max_tokens * 0.8:
                    test_code = test_info['code']
                    context_parts.append(f"\n### {test_info['node'].full_path}\n```python\n{test_code}\n```\n")
                    tokens_used += self._estimate_tokens(test_code)
                    tests_added += 1

        if verbose:
            print(f"      ✓ Related tests: {tests_added}/{len(tests)} included")
            print(f"\n    🔍 Level 3 - Metadata:")

        # Priority 5: Metadata (always fits)
        metadata = self._build_metadata_summary(changed_node)
        context_parts.append(f"\n## Additional Context\n{metadata}\n")

        if verbose:
            imports = self._get_file_imports(changed_node)
            print(f"      ✓ File imports: {len(imports)}")
            print(f"      ✓ File location: {changed_node.filepath}:{changed_node.start_line}-{changed_node.end_line}")
            print(f"\n    📈 Total tokens used: {tokens_used}/{max_tokens} ({int(tokens_used/max_tokens*100)}%)")

        return '\n'.join(context_parts)

    def _get_node_code(self, node: object) -> str:
        """Extract source code for a node"""
        try:
            filepath = f"{self.repository_path}/{node.filepath}"
            with open(filepath, 'r') as f:
                lines = f.readlines()
                # Get lines for this node (0-indexed)
                code_lines = lines[node.start_line - 1:node.end_line]
                return ''.join(code_lines)
        except Exception as e:
            return f"# Could not read source code: {e}"

    def _get_immediate_callers(self, node: object) -> List[Dict]:
        """Get immediate callers with their code"""
        callers = []
        for caller_path in node.called_by[:10]:  # Limit to top 10
            if caller_path in self.node_map:
                caller_node = self.node_map[caller_path]
                caller_code = self._get_node_code(caller_node)
                callers.append({'node': caller_node, 'code': caller_code})
        return callers

    def _get_immediate_callees(self, node: object) -> List[Dict]:
        """Get immediate callees with their code"""
        callees = []
        for callee_path in node.calls[:10]:  # Limit to top 10
            if callee_path in self.node_map:
                callee_node = self.node_map[callee_path]
                callee_code = self._get_node_code(callee_node)
                callees.append({'node': callee_node, 'code': callee_code})
        return callees

    def _get_parent_class(self, node: object) -> Optional[Dict]:
        """Get parent class if this is a method"""
        if node.parent_class:
            # Find the class node
            class_path = f"{node.filepath}::{node.parent_class}"
            if class_path in self.node_map:
                class_node = self.node_map[class_path]
                class_code = self._get_node_code(class_node)
                return {'node': class_node, 'code': class_code}
        return None

    def _get_related_tests(self, node: object) -> List[Dict]:
        """Find related test files/functions"""
        tests = []

        # Look for test files that might test this function
        test_name_patterns = [
            f"test_{node.name}",
            f"test{node.name.capitalize()}",
            node.name.replace('_', '').lower()
        ]

        for test_node in self.nodes:
            if test_node.node_type in ['function', 'method']:
                # Check if it's in a test file
                if 'test' in test_node.filepath.lower():
                    # Check if test name matches
                    for pattern in test_name_patterns:
                        if pattern in test_node.name.lower():
                            test_code = self._get_node_code(test_node)
                            tests.append({'node': test_node, 'code': test_code})
                            break

        return tests[:5]  # Limit to 5 tests

    def _get_file_imports(self, node: object) -> List[str]:
        """Get imports from the file"""
        try:
            filepath = f"{self.repository_path}/{node.filepath}"
            with open(filepath, 'r') as f:
                lines = f.readlines()

            imports = []
            for line in lines[:50]:  # Check first 50 lines
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)

            return imports
        except Exception:
            return []

    def _build_metadata_summary(self, node: object) -> str:
        """Build metadata summary (Level 3 context)"""
        parts = []

        # File and location
        parts.append(f"- **File**: `{node.filepath}`")
        parts.append(f"- **Lines**: {node.start_line}-{node.end_line}")
        parts.append(f"- **Type**: {node.node_type}")
        parts.append(f"- **Language**: {node.language}")

        # Call graph stats
        parts.append(f"- **Called by**: {len(node.called_by)} function(s)")
        parts.append(f"- **Calls**: {len(node.calls)} function(s)")

        # Parameters
        if node.parameters:
            parts.append(f"- **Parameters**: `{', '.join(node.parameters)}`")

        # Return type
        if node.return_type:
            parts.append(f"- **Return Type**: `{node.return_type}`")

        # Parent class
        if node.parent_class:
            parts.append(f"- **Parent Class**: `{node.parent_class}`")

        return '\n'.join(parts)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation)
        ~1 token per 4 characters for English text
        """
        return len(text) // 4
