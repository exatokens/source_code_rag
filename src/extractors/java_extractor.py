"""
Java-specific code extractor (with enum and interface support)
"""
from src.extractors.base_extractor import BaseExtractor
from src.models.semantic_node import SemanticNode


class JavaExtractor(BaseExtractor):
    """Extract semantic nodes from Java code - WITH ENUM AND INTERFACE SUPPORT"""

    def extract(self, root_node, source_code, filepath):
        """Extract nodes from Java code"""

        def walk(node, parent_class=None):
            # Java class: class_declaration
            if node.type == 'class_declaration':
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
                    language='java'
                )
                class_node.qualified_name = class_name
                class_node.full_path = f"{filepath}::{class_name}"

                self.nodes.append(class_node)
                self.node_map[class_node.full_path] = class_node

                # Walk class body
                body = node.child_by_field_name('body')
                if body:
                    for child in body.children:
                        walk(child, parent_class=class_name)

            # Java enum: enum_declaration
            elif node.type == 'enum_declaration':
                name_node = node.child_by_field_name('name')
                if not name_node:
                    return

                enum_name = source_code[name_node.start_byte:name_node.end_byte].decode()

                enum_node = SemanticNode(
                    name=enum_name,
                    node_type='enum',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    filepath=filepath,
                    language='java'
                )
                enum_node.qualified_name = enum_name
                enum_node.full_path = f"{filepath}::{enum_name}"

                self.nodes.append(enum_node)
                self.node_map[enum_node.full_path] = enum_node

                # Walk enum body (enums can have methods too!)
                body = node.child_by_field_name('body')
                if body:
                    for child in body.children:
                        walk(child, parent_class=enum_name)

            # Java interface: interface_declaration
            elif node.type == 'interface_declaration':
                name_node = node.child_by_field_name('name')
                if not name_node:
                    return

                interface_name = source_code[name_node.start_byte:name_node.end_byte].decode()

                interface_node = SemanticNode(
                    name=interface_name,
                    node_type='interface',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    filepath=filepath,
                    language='java'
                )
                interface_node.qualified_name = interface_name
                interface_node.full_path = f"{filepath}::{interface_name}"

                self.nodes.append(interface_node)
                self.node_map[interface_node.full_path] = interface_node

                # Walk interface body
                body = node.child_by_field_name('body')
                if body:
                    for child in body.children:
                        walk(child, parent_class=interface_name)

            # Java method: method_declaration
            elif node.type == 'method_declaration':
                name_node = node.child_by_field_name('name')
                if not name_node:
                    return

                method_name = source_code[name_node.start_byte:name_node.end_byte].decode()

                method_node = SemanticNode(
                    name=method_name,
                    node_type='method' if parent_class else 'function',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    filepath=filepath,
                    language='java'
                )

                if parent_class:
                    method_node.parent_class = parent_class
                    method_node.qualified_name = f"{parent_class}.{method_name}"
                    method_node.full_path = f"{filepath}::{parent_class}.{method_name}"
                else:
                    method_node.qualified_name = method_name
                    method_node.full_path = f"{filepath}::{method_name}"

                # Extract parameters
                params_node = node.child_by_field_name('parameters')
                if params_node:
                    for child in params_node.children:
                        if child.type == 'formal_parameter':
                            param_name_node = child.child_by_field_name('name')
                            if param_name_node:
                                param = source_code[param_name_node.start_byte:param_name_node.end_byte].decode()
                                method_node.parameters.append(param)

                # Extract return type
                type_node = node.child_by_field_name('type')
                if type_node:
                    return_type = source_code[type_node.start_byte:type_node.end_byte].decode()
                    method_node.return_type = return_type

                # Find calls
                method_node.calls = self.find_calls(node, source_code, parent_class, filepath)

                self.nodes.append(method_node)
                self.node_map[method_node.full_path] = method_node

            else:
                for child in node.children:
                    walk(child, parent_class=parent_class)

        walk(root_node)
        return self.nodes

    def find_calls(self, func_node, source_code, parent_class, filepath):
        """Find method calls in Java"""
        calls = []

        def walk(node):
            if node.type == 'method_invocation':
                name_node = node.child_by_field_name('name')
                if name_node:
                    method_name = source_code[name_node.start_byte:name_node.end_byte].decode()

                    object_node = node.child_by_field_name('object')
                    if object_node:
                        obj_name = source_code[object_node.start_byte:object_node.end_byte].decode()
                        if obj_name == 'this' and parent_class:
                            qualified = f"{filepath}::{parent_class}.{method_name}"
                        elif obj_name == parent_class:
                            qualified = f"{filepath}::{parent_class}.{method_name}"
                        else:
                            qualified = f"{filepath}::{obj_name}.{method_name}"
                    else:
                        if parent_class:
                            qualified = f"{filepath}::{parent_class}.{method_name}"
                        else:
                            qualified = f"{filepath}::{method_name}"

                    calls.append(qualified)

            for child in node.children:
                walk(child)

        walk(func_node)
        return calls
