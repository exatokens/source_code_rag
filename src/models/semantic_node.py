"""
Core semantic node model representing code entities
"""

class SemanticNode:
    """
    Represents a semantic code entity (class, function, method, enum, interface)
    """

    def __init__(self, name, node_type, start_line, end_line, filepath=None, language=None):
        self.name = name
        self.node_type = node_type  # 'class', 'enum', 'interface', 'function', 'method'
        self.start_line = start_line
        self.end_line = end_line
        self.filepath = filepath
        self.language = language
        self.parent_class = None
        self.qualified_name = None
        self.full_path = None
        self.calls = []
        self.called_by = []
        self.parameters = []
        self.return_type = None

    def __repr__(self):
        return f"<{self.full_path}:{self.start_line}>"
