"""
Call graph builder for building dependency relationships
"""


class CallGraphBuilder:
    """Build called_by relationships between nodes"""

    @staticmethod
    def build_call_graph(nodes, node_map):
        """
        Build called_by relationships

        Args:
            nodes: List of SemanticNode objects
            node_map: Dictionary mapping full_path to SemanticNode

        Returns:
            Updated nodes with called_by relationships
        """
        print("Building call graph...")

        for node in nodes:
            for called_path in node.calls:
                if called_path in node_map:
                    target_node = node_map[called_path]
                    target_node.called_by.append(node.full_path)

        return nodes
