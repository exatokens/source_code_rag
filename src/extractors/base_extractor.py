"""
Base extractor class for language-specific code extractors
"""
from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """
    Abstract base class for language-specific extractors
    """

    def __init__(self):
        self.nodes = []
        self.node_map = {}

    @abstractmethod
    def extract(self, root_node, source_code, filepath):
        """
        Extract semantic nodes from AST

        Args:
            root_node: Tree-sitter root node
            source_code: Source code bytes
            filepath: Relative file path

        Returns:
            List of SemanticNode objects
        """
        pass

    @abstractmethod
    def find_calls(self, func_node, source_code, context, filepath):
        """
        Find function/method calls within a function

        Args:
            func_node: Tree-sitter function node
            source_code: Source code bytes
            context: Language-specific context (e.g., parent_class)
            filepath: Relative file path

        Returns:
            List of qualified call paths
        """
        pass
