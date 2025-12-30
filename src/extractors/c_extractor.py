"""
C-specific code extractor
"""
from src.extractors.base_extractor import BaseExtractor
from src.models.semantic_node import SemanticNode


class CExtractor(BaseExtractor):
    """Extract semantic nodes from C code"""

    def extract(self, root_node, source_code, filepath):
        """Extract nodes from C code"""

        def walk(node):
            if node.type == 'function_definition':
                declarator = node.child_by_field_name('declarator')
                if not declarator:
                    return

                func_name = self._get_function_name(declarator, source_code)
                if not func_name:
                    return

                func_node = SemanticNode(
                    name=func_name,
                    node_type='function',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    filepath=filepath,
                    language='c'
                )

                func_node.qualified_name = func_name
                func_node.full_path = f"{filepath}::{func_name}"

                params = self._get_parameters(declarator, source_code)
                func_node.parameters = params

                type_node = node.child_by_field_name('type')
                if type_node:
                    return_type = source_code[type_node.start_byte:type_node.end_byte].decode()
                    func_node.return_type = return_type

                func_node.calls = self.find_calls(node, source_code, None, filepath)

                self.nodes.append(func_node)
                self.node_map[func_node.full_path] = func_node

            for child in node.children:
                walk(child)

        walk(root_node)
        return self.nodes

    def _get_function_name(self, declarator, source_code):
        """Extract function name from C declarator"""
        if declarator.type == 'function_declarator':
            inner = declarator.child_by_field_name('declarator')
            if inner and inner.type == 'identifier':
                return source_code[inner.start_byte:inner.end_byte].decode()
        elif declarator.type == 'identifier':
            return source_code[declarator.start_byte:declarator.end_byte].decode()
        return None

    def _get_parameters(self, declarator, source_code):
        """Extract parameters from C function"""
        params = []
        if declarator.type == 'function_declarator':
            param_list = declarator.child_by_field_name('parameters')
            if param_list:
                for child in param_list.children:
                    if child.type == 'parameter_declaration':
                        decl = child.child_by_field_name('declarator')
                        if decl and decl.type == 'identifier':
                            param = source_code[decl.start_byte:decl.end_byte].decode()
                            params.append(param)
        return params

    def find_calls(self, func_node, source_code, context, filepath):
        """Find function calls in C"""
        calls = []

        def walk(node):
            if node.type == 'call_expression':
                func = node.child_by_field_name('function')
                if func and func.type == 'identifier':
                    func_name = source_code[func.start_byte:func.end_byte].decode()
                    qualified = f"{filepath}::{func_name}"
                    calls.append(qualified)

            for child in node.children:
                walk(child)

        walk(func_node)
        return calls
