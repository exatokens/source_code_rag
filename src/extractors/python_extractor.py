"""
Python-specific code extractor
"""
from src.extractors.base_extractor import BaseExtractor
from src.models.semantic_node import SemanticNode


class PythonExtractor(BaseExtractor):
    """Extract semantic nodes from Python code"""

    def extract(self, root_node, source_code, filepath):
        """Extract nodes from Python code"""

        def walk(node, parent_class=None):
            if node.type == 'class_definition':
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
                    language='python'
                )
                class_node.qualified_name = class_name
                class_node.full_path = f"{filepath}::{class_name}"

                self.nodes.append(class_node)
                self.node_map[class_node.full_path] = class_node

                for child in node.children:
                    walk(child, parent_class=class_name)

            elif node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if not name_node:
                    return

                func_name = source_code[name_node.start_byte:name_node.end_byte].decode()

                func_node = SemanticNode(
                    name=func_name,
                    node_type='method' if parent_class else 'function',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    filepath=filepath,
                    language='python'
                )

                if parent_class:
                    func_node.parent_class = parent_class
                    func_node.qualified_name = f"{parent_class}.{func_name}"
                    func_node.full_path = f"{filepath}::{parent_class}.{func_name}"
                else:
                    func_node.qualified_name = func_name
                    func_node.full_path = f"{filepath}::{func_name}"

                # Extract parameters
                params_node = node.child_by_field_name('parameters')
                if params_node:
                    for child in params_node.children:
                        if child.type == 'identifier':
                            param = source_code[child.start_byte:child.end_byte].decode()
                            func_node.parameters.append(param)

                # Find calls
                func_node.calls = self.find_calls(node, source_code, parent_class, filepath)

                self.nodes.append(func_node)
                self.node_map[func_node.full_path] = func_node

            else:
                for child in node.children:
                    walk(child, parent_class=parent_class)

        walk(root_node)
        return self.nodes

    def find_calls(self, func_node, source_code, parent_class, filepath):
        """Find function calls in Python"""
        calls = []

        def walk(node):
            if node.type == 'call':
                func_name_node = node.child_by_field_name('function')

                if func_name_node:
                    if func_name_node.type == 'identifier':
                        called_name = source_code[func_name_node.start_byte:func_name_node.end_byte].decode()
                        qualified = f"{filepath}::{called_name}"
                        calls.append(qualified)

                    elif func_name_node.type == 'attribute':
                        obj_node = func_name_node.child_by_field_name('object')
                        attr_node = func_name_node.child_by_field_name('attribute')

                        if obj_node and attr_node:
                            obj_name = source_code[obj_node.start_byte:obj_node.end_byte].decode()
                            method_name = source_code[attr_node.start_byte:attr_node.end_byte].decode()

                            if obj_name == 'self' and parent_class:
                                qualified = f"{filepath}::{parent_class}.{method_name}"
                            elif obj_name == parent_class:
                                qualified = f"{filepath}::{parent_class}.{method_name}"
                            else:
                                qualified = f"{filepath}::{obj_name}.{method_name}"
                            calls.append(qualified)

            for child in node.children:
                walk(child)

        walk(func_node)
        return calls
