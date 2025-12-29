from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_java as tsjava
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
import os
from collections import defaultdict

class SemanticNode:
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


class LanguageDetector:
    """Detect programming language from file extension"""
    
    LANGUAGE_MAP = {
        '.py': 'python',
        '.java': 'java',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.hpp': 'cpp',
        '.hxx': 'cpp',
        '.hh': 'cpp',
    }
    
    @staticmethod
    def detect(filepath):
        _, ext = os.path.splitext(filepath)
        return LanguageDetector.LANGUAGE_MAP.get(ext.lower())


class MultiLanguageScanner:
    """Multi-language repository scanner supporting Python, Java, C, C++"""
    
    DEFAULT_IGNORE = {
        '.git', '.svn', 'node_modules', '__pycache__', '.venv', 'venv',
        'env', 'build', 'dist', '.idea', '.vscode', 'target', 'out',
        '.pytest_cache', '.mypy_cache', 'htmlcov', '.tox', 'eggs',
        '*.egg-info', '.eggs', 'migrations', 'tests', 'test',
    }
    
    def __init__(self, ignore_patterns=None):
        self.parsers = {}
        self.nodes = []
        self.node_map = {}
        self.file_count = 0
        self.error_count = 0
        
        self.ignore_patterns = self.DEFAULT_IGNORE.copy()
        if ignore_patterns:
            self.ignore_patterns.update(ignore_patterns)
        
        self._setup_parsers()
    
    def _setup_parsers(self):
        """Initialize parsers for all supported languages"""
        try:
            py_lang = Language(tspython.language())
            self.parsers['python'] = Parser(py_lang)
            print("✓ Python parser loaded")
        except Exception as e:
            print(f"✗ Python parser failed: {e}")
        
        try:
            java_lang = Language(tsjava.language())
            self.parsers['java'] = Parser(java_lang)
            print("✓ Java parser loaded")
        except Exception as e:
            print(f"✗ Java parser failed: {e}")
        
        try:
            c_lang = Language(tsc.language())
            self.parsers['c'] = Parser(c_lang)
            print("✓ C parser loaded")
        except Exception as e:
            print(f"✗ C parser failed: {e}")
        
        try:
            cpp_lang = Language(tscpp.language())
            self.parsers['cpp'] = Parser(cpp_lang)
            print("✓ C++ parser loaded")
        except Exception as e:
            print(f"✗ C++ parser failed: {e}")
    
    def should_ignore(self, path):
        """Check if path should be ignored"""
        basename = os.path.basename(path)
        
        if basename in self.ignore_patterns:
            return True
        
        for pattern in self.ignore_patterns:
            if pattern in path:
                return True
        
        if basename.startswith('.') and basename != '.':
            return True
        
        return False
    
    def scan_repository(self, repo_path):
        """Scan entire repository"""
        print(f"\nScanning repository: {repo_path}\n")
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not self.should_ignore(os.path.join(root, d))]
            
            for filename in files:
                filepath = os.path.join(root, filename)
                
                if self.should_ignore(filepath):
                    continue
                
                language = LanguageDetector.detect(filepath)
                if not language or language not in self.parsers:
                    continue
                
                rel_path = os.path.relpath(filepath, repo_path)
                
                try:
                    print(f"  [{language:6}] Parsing: {rel_path}")
                    self.scan_file(filepath, rel_path, language)
                    self.file_count += 1
                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    self.error_count += 1
        
        print(f"\n{'='*60}")
        print(f"✓ Successfully parsed: {self.file_count} files")
        print(f"✗ Errors: {self.error_count} files")
        
        # Enhanced statistics
        type_counts = defaultdict(int)
        for node in self.nodes:
            type_counts[node.node_type] += 1
        
        print(f"✓ Total classes: {type_counts['class']}")
        print(f"✓ Total enums: {type_counts['enum']}")
        print(f"✓ Total interfaces: {type_counts['interface']}")
        print(f"✓ Total functions: {type_counts['function']}")
        print(f"✓ Total methods: {type_counts['method']}")
        print(f"{'='*60}\n")
        
        print("Building call graph...")
        self.build_call_graph()
        
        return self.nodes
    
    def scan_file(self, filepath, rel_path, language):
        """Scan a single file"""
        with open(filepath, 'rb') as f:
            source_code = f.read()
        
        tree = self.parsers[language].parse(source_code)
        
        # Route to language-specific extractor
        if language == 'python':
            self._extract_python(tree.root_node, source_code, rel_path)
        elif language == 'java':
            self._extract_java(tree.root_node, source_code, rel_path)
        elif language == 'c':
            self._extract_c(tree.root_node, source_code, rel_path)
        elif language == 'cpp':
            self._extract_cpp(tree.root_node, source_code, rel_path)
    
    # ==================== PYTHON EXTRACTOR ====================
    
    def _extract_python(self, root_node, source_code, filepath):
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
                func_node.calls = self._find_calls_python(node, source_code, parent_class, filepath)
                
                self.nodes.append(func_node)
                self.node_map[func_node.full_path] = func_node
            
            else:
                for child in node.children:
                    walk(child, parent_class=parent_class)
        
        walk(root_node)
    
    def _find_calls_python(self, func_node, source_code, parent_class, filepath):
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
    
    # ==================== JAVA EXTRACTOR (ENHANCED) ====================
    
    def _extract_java(self, root_node, source_code, filepath):
        """Extract nodes from Java code - WITH ENUM AND INTERFACE SUPPORT"""
        
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
            
            # Java enum: enum_declaration (NEW!)
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
            
            # Java interface: interface_declaration (NEW!)
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
                method_node.calls = self._find_calls_java(node, source_code, parent_class, filepath)
                
                self.nodes.append(method_node)
                self.node_map[method_node.full_path] = method_node
            
            else:
                for child in node.children:
                    walk(child, parent_class=parent_class)
        
        walk(root_node)
    
    def _find_calls_java(self, func_node, source_code, parent_class, filepath):
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
    
    # ==================== C EXTRACTOR ====================
    
    def _extract_c(self, root_node, source_code, filepath):
        """Extract nodes from C code"""
        
        def walk(node):
            if node.type == 'function_definition':
                declarator = node.child_by_field_name('declarator')
                if not declarator:
                    return
                
                func_name = self._get_c_function_name(declarator, source_code)
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
                
                params = self._get_c_parameters(declarator, source_code)
                func_node.parameters = params
                
                type_node = node.child_by_field_name('type')
                if type_node:
                    return_type = source_code[type_node.start_byte:type_node.end_byte].decode()
                    func_node.return_type = return_type
                
                func_node.calls = self._find_calls_c(node, source_code, filepath)
                
                self.nodes.append(func_node)
                self.node_map[func_node.full_path] = func_node
            
            for child in node.children:
                walk(child)
        
        walk(root_node)
    
    def _get_c_function_name(self, declarator, source_code):
        """Extract function name from C declarator"""
        if declarator.type == 'function_declarator':
            inner = declarator.child_by_field_name('declarator')
            if inner and inner.type == 'identifier':
                return source_code[inner.start_byte:inner.end_byte].decode()
        elif declarator.type == 'identifier':
            return source_code[declarator.start_byte:declarator.end_byte].decode()
        return None
    
    def _get_c_parameters(self, declarator, source_code):
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
    
    def _find_calls_c(self, func_node, source_code, filepath):
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
    
    # ==================== C++ EXTRACTOR ====================
    
    def _extract_cpp(self, root_node, source_code, filepath):
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
                
                func_name = self._get_cpp_function_name(declarator, source_code)
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
                
                params = self._get_cpp_parameters(declarator, source_code)
                func_node.parameters = params
                
                type_node = node.child_by_field_name('type')
                if type_node:
                    return_type = source_code[type_node.start_byte:type_node.end_byte].decode()
                    func_node.return_type = return_type
                
                func_node.calls = self._find_calls_cpp(node, source_code, parent_class, filepath)
                
                self.nodes.append(func_node)
                self.node_map[func_node.full_path] = func_node
            
            else:
                for child in node.children:
                    walk(child, parent_class=parent_class, namespace=namespace)
        
        walk(root_node)
    
    def _get_cpp_function_name(self, declarator, source_code):
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
    
    def _get_cpp_parameters(self, declarator, source_code):
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
    
    def _find_calls_cpp(self, func_node, source_code, parent_class, filepath):
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
    
    # ==================== COMMON METHODS ====================
    
    def build_call_graph(self):
        """Build called_by relationships"""
        for node in self.nodes:
            for called_path in node.calls:
                if called_path in self.node_map:
                    target_node = self.node_map[called_path]
                    target_node.called_by.append(node.full_path)
    
    def get_statistics(self):
        """Get repository statistics"""
        stats = {
            'total_files': self.file_count,
            'total_classes': len([n for n in self.nodes if n.node_type == 'class']),
            'total_enums': len([n for n in self.nodes if n.node_type == 'enum']),
            'total_interfaces': len([n for n in self.nodes if n.node_type == 'interface']),
            'total_functions': len([n for n in self.nodes if n.node_type == 'function']),
            'total_methods': len([n for n in self.nodes if n.node_type == 'method']),
            'by_language': defaultdict(lambda: {'classes': 0, 'enums': 0, 'interfaces': 0, 'functions': 0, 'methods': 0}),
            'files': defaultdict(lambda: {'classes': 0, 'enums': 0, 'interfaces': 0, 'functions': 0, 'methods': 0})
        }
        
        for node in self.nodes:
            lang = node.language
            node_type = node.node_type
            
            if node_type in ['class', 'enum', 'interface', 'function', 'method']:
                stats['by_language'][lang][f"{node_type}s" if node_type != 'class' else 'classes'] += 1
                stats['files'][node.filepath][f"{node_type}s" if node_type != 'class' else 'classes'] += 1
        
        return stats
    
    def print_summary(self):
        """Print a summary of the scan"""
        stats = self.get_statistics()
        
        print("\n" + "="*70)
        print("REPOSITORY SUMMARY")
        print("="*70)
        print(f"Total Files: {stats['total_files']}")
        print(f"Total Classes: {stats['total_classes']}")
        print(f"Total Enums: {stats['total_enums']}")
        print(f"Total Interfaces: {stats['total_interfaces']}")
        print(f"Total Functions: {stats['total_functions']}")
        print(f"Total Methods: {stats['total_methods']}")
        
        print("\nBy Language:")
        for lang, counts in stats['by_language'].items():
            print(f"\n  {lang.upper()}:")
            print(f"    Classes: {counts['classes']}")
            print(f"    Enums: {counts['enums']}")
            print(f"    Interfaces: {counts['interfaces']}")
            print(f"    Functions: {counts['functions']}")
            print(f"    Methods: {counts['methods']}")
        
        print("\nTop 10 Files by Function Count:")
        sorted_files = sorted(
            stats['files'].items(),
            key=lambda x: x[1]['functions'] + x[1]['methods'],
            reverse=True
        )[:10]
        
        for filepath, counts in sorted_files:
            total = counts['functions'] + counts['methods']
            types = counts['classes'] + counts['enums'] + counts['interfaces']
            print(f"  {filepath}:")
            print(f"    {total} functions/methods ({counts['classes']} classes, {counts['enums']} enums, {counts['interfaces']} interfaces)")
    
    def search_function(self, func_name):
        """Search for functions by name"""
        results = []
        for node in self.nodes:
            if node.name == func_name and node.node_type in ['function', 'method']:
                results.append(node)
        return results
    
    def search_type(self, type_name):
        """Search for classes, enums, or interfaces by name"""
        results = []
        for node in self.nodes:
            if node.name == type_name and node.node_type in ['class', 'enum', 'interface']:
                results.append(node)
        return results
    
    def print_function_details(self, func_name):
        """Print details for a specific function"""
        results = self.search_function(func_name)
        
        if not results:
            print(f"\nNo function named '{func_name}' found.")
            return
        
        print(f"\n{'='*70}")
        print(f"FUNCTION DETAILS: {func_name}")
        print(f"{'='*70}")
        
        for node in results:
            print(f"\n{node.full_path} [{node.language}]")
            print(f"  Type: {node.node_type}")
            print(f"  Lines: {node.start_line}-{node.end_line}")
            if node.parent_class:
                print(f"  Parent: {node.parent_class}")
            if node.return_type:
                print(f"  Return Type: {node.return_type}")
            print(f"  Parameters: {node.parameters}")
            print(f"  Calls: {len(node.calls)} functions")
            for call in node.calls[:10]:
                print(f"    -> {call}")
            if len(node.calls) > 10:
                print(f"    ... and {len(node.calls) - 10} more")
            print(f"  Called by: {len(node.called_by)} functions")
            for caller in node.called_by[:10]:
                print(f"    <- {caller}")
            if len(node.called_by) > 10:
                print(f"    ... and {len(node.called_by) - 10} more")
    
    def print_type_details(self, type_name):
        """Print details for a specific class, enum, or interface"""
        results = self.search_type(type_name)
        
        if not results:
            print(f"\nNo type named '{type_name}' found.")
            return
        
        for type_node in results:
            methods = [n for n in self.nodes if n.parent_class == type_name and n.node_type == 'method']
            
            print(f"\n{'='*70}")
            print(f"{type_node.node_type.upper()} DETAILS: {type_name} [{type_node.language}]")
            print(f"{'='*70}")
            
            print(f"\nLocation: {type_node.full_path}")
            print(f"Lines: {type_node.start_line}-{type_node.end_line}")
            print(f"Total Methods: {len(methods)}")
            
            if methods:
                print(f"\nMethods:")
                for method in sorted(methods, key=lambda m: m.start_line):
                    params_str = ', '.join(method.parameters) if method.parameters else ''
                    return_type_str = f" -> {method.return_type}" if method.return_type else ""
                    print(f"  • {method.name}({params_str}){return_type_str}")
                    print(f"      Line {method.start_line} | Calls: {len(method.calls)} | Called by: {len(method.called_by)}")
            
            if methods:
                print(f"\nMost Called Methods:")
                sorted_methods = sorted(methods, key=lambda m: len(m.called_by), reverse=True)[:5]
                for method in sorted_methods:
                    if method.called_by:
                        print(f"  • {method.name}: called {len(method.called_by)} times")
                        for caller in method.called_by[:3]:
                            print(f"      <- {caller}")
                        if len(method.called_by) > 3:
                            print(f"      ... and {len(method.called_by) - 3} more")
    
    def print_all_types(self):
        """Print all classes, enums, and interfaces"""
        types = [n for n in self.nodes if n.node_type in ['class', 'enum', 'interface']]
        
        print("\n" + "="*70)
        print("ALL TYPES (Classes, Enums, Interfaces)")
        print("="*70)
        
        types_by_file = defaultdict(list)
        for node in types:
            types_by_file[node.filepath].append(node)
        
        for filepath in sorted(types_by_file.keys()):
            print(f"\n{filepath}:")
            for node in sorted(types_by_file[filepath], key=lambda n: n.start_line):
                method_count = len([n for n in self.nodes if n.parent_class == node.name])
                type_label = f"[{node.node_type}]"
                print(f"  • {node.name} {type_label:12} [{node.start_line}] - {method_count} methods")


if __name__ == "__main__":
    scanner = MultiLanguageScanner()
    
    # repo path
    repo_path = '/Users/siva/sandbox/spring-boot'
    
    scanner.scan_repository(repo_path)
    scanner.print_summary()
    
    # New methods:
    # scanner.print_type_details('KafkaProperties')  # Works for class, enum, or interface
    # scanner.print_all_types()  # Show all classes, enums, interfaces
