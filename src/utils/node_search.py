"""
Node search and query utilities
"""


class NodeSearch:
    """Search and query semantic nodes"""

    @staticmethod
    def search_function(nodes, func_name):
        """
        Search for functions by name

        Args:
            nodes: List of SemanticNode objects
            func_name: Function name to search for

        Returns:
            List of matching SemanticNode objects
        """
        results = []
        for node in nodes:
            if node.name == func_name and node.node_type in ['function', 'method']:
                results.append(node)
        return results

    @staticmethod
    def search_type(nodes, type_name):
        """
        Search for classes, enums, or interfaces by name

        Args:
            nodes: List of SemanticNode objects
            type_name: Type name to search for

        Returns:
            List of matching SemanticNode objects
        """
        results = []
        for node in nodes:
            if node.name == type_name and node.node_type in ['class', 'enum', 'interface']:
                results.append(node)
        return results
