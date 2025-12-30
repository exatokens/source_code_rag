"""
C++ specific code extractor
"""
from src.extractors.base_extractor import BaseExtractor
from src.models.semantic_node import SemanticNode


class CppExtractor(BaseExtractor):
    """Extract semantic nodes from C++ code"""

    def extract(self, root_node, source_code, filepath):
        """Extract nodes from C++ code"""

        def walk(node, parent_class=None, namespace=None):
            if node.type == 'class_specifier':
                name_node = node.child_by_field_name('name')
                if not name_node:
                    return

                class_name = source_code[name_node.start_byte:name_node.end_byte].decode()

                class_node = SemanticNode(
                    name=class_name,
                    node_type='class',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    filepath=filepath,
                    language='cpp'
                )
                class_node.qualified_name = class_name
                class_node.full_path = f"{filepath}::{class_name}"

                self.nodes.append(class_node)
                self.node_map[class_node.full_path] = class_node

                body = node.child_by_field_name('body')
                if body:
                    for child in body.children:
                        walk(child, parent_class=class_name, namespace=namespace)

            elif node.type == 'function_definition':
                declarator = node.child_by_field_name('declarator')
                if not declarator:
                    return

                func_name = self._get_function_name(declarator, source_code)
                if not func_name:
                    return

                func_node = SemanticNode(
                    name=func_name,
                    node_type='method' if parent_class else 'function',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    filepath=filepath,
                    language='cpp'
                )

                if parent_class:
                    func_node.parent_class = parent_class
                    func_node.qualified_name = f"{parent_class}.{func_name}"
                    func_node.full_path = f"{filepath}::{parent_class}.{func_name}"
                else:
                    func_node.qualified_name = func_name
                    func_node.full_path = f"{filepath}::{func_name}"

                params = self._get_parameters(declarator, source_code)
                func_node.parameters = params

                type_node = node.child_by_field_name('type')
                if type_node:
                    return_type = source_code[type_node.start_byte:type_node.end_byte].decode()
                    func_node.return_type = return_type

                func_node.calls = self.find_calls(node, source_code, parent_class, filepath)

                self.nodes.append(func_node)
                self.node_map[func_node.full_path] = func_node

            else:
                for child in node.children:
                    walk(child, parent_class=parent_class, namespace=namespace)

        walk(root_node)
        return self.nodes

    def _get_function_name(self, declarator, source_code):
        """Extract function name from C++ declarator"""
        if declarator.type == 'function_declarator':
            inner = declarator.child_by_field_name('declarator')
            if inner:
                if inner.type == 'identifier':
                    return source_code[inner.start_byte:inner.end_byte].decode()
                elif inner.type == 'field_identifier':
                    return source_code[inner.start_byte:inner.end_byte].decode()
        elif declarator.type == 'identifier':
            return source_code[declarator.start_byte:declarator.end_byte].decode()
        return None

    def _get_parameters(self, declarator, source_code):
        """Extract parameters from C++ function"""
        params = []
        if declarator.type == 'function_declarator':
            param_list = declarator.child_by_field_name('parameters')
            if param_list:
                for child in param_list.children:
                    if child.type == 'parameter_declaration':
                        decl = child.child_by_field_name('declarator')
                        if decl:
                            if decl.type == 'identifier':
                                param = source_code[decl.start_byte:decl.end_byte].decode()
                                params.append(param)
        return params

    def find_calls(self, func_node, source_code, parent_class, filepath):
        """Find function calls in C++"""
        calls = []

        def walk(node):
            if node.type == 'call_expression':
                func = node.child_by_field_name('function')
                if func:
                    if func.type == 'identifier':
                        func_name = source_code[func.start_byte:func.end_byte].decode()
                        if parent_class:
                            qualified = f"{filepath}::{parent_class}.{func_name}"
                        else:
                            qualified = f"{filepath}::{func_name}"
                        calls.append(qualified)
                    elif func.type == 'field_expression':
                        field = func.child_by_field_name('field')
                        if field:
                            method_name = source_code[field.start_byte:field.end_byte].decode()
                            obj = func.child_by_field_name('argument')
                            if obj:
                                obj_name = source_code[obj.start_byte:obj.end_byte].decode()
                                if obj_name == 'this' and parent_class:
                                    qualified = f"{filepath}::{parent_class}.{method_name}"
                                else:
                                    qualified = f"{filepath}::{obj_name}.{method_name}"
                                calls.append(qualified)

            for child in node.children:
                walk(child)

        walk(func_node)
        return calls
