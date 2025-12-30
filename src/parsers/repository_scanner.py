"""
Multi-language repository scanner
"""
import os
from collections import defaultdict
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_java as tsjava
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp

from src.utils.language_detector import LanguageDetector
from src.extractors.python_extractor import PythonExtractor
from src.extractors.java_extractor import JavaExtractor
from src.extractors.c_extractor import CExtractor
from src.extractors.cpp_extractor import CppExtractor


class RepositoryScanner:
    """Multi-language repository scanner supporting Python, Java, C, C++"""

    DEFAULT_IGNORE = {
        '.git', '.svn', 'node_modules', '__pycache__', '.venv', 'venv',
        'env', 'build', 'dist', '.idea', '.vscode', 'target', 'out',
        '.pytest_cache', '.mypy_cache', 'htmlcov', '.tox', 'eggs',
        '*.egg-info', '.eggs', 'migrations', 'tests', 'test',
    }

    def __init__(self, ignore_patterns=None):
        self.parsers = {}
        self.extractors = {}
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
            self.extractors['python'] = PythonExtractor()
            print("✓ Python parser loaded")
        except Exception as e:
            print(f"✗ Python parser failed: {e}")

        try:
            java_lang = Language(tsjava.language())
            self.parsers['java'] = Parser(java_lang)
            self.extractors['java'] = JavaExtractor()
            print("✓ Java parser loaded")
        except Exception as e:
            print(f"✗ Java parser failed: {e}")

        try:
            c_lang = Language(tsc.language())
            self.parsers['c'] = Parser(c_lang)
            self.extractors['c'] = CExtractor()
            print("✓ C parser loaded")
        except Exception as e:
            print(f"✗ C parser failed: {e}")

        try:
            cpp_lang = Language(tscpp.language())
            self.parsers['cpp'] = Parser(cpp_lang)
            self.extractors['cpp'] = CppExtractor()
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

        self._print_scan_summary()
        return self.nodes

    def scan_file(self, filepath, rel_path, language):
        """Scan a single file"""
        with open(filepath, 'rb') as f:
            source_code = f.read()

        tree = self.parsers[language].parse(source_code)
        extractor = self.extractors[language]

        # Extract nodes
        extracted_nodes = extractor.extract(tree.root_node, source_code, rel_path)

        # Merge nodes and node_map
        self.nodes.extend(extracted_nodes)
        self.node_map.update(extractor.node_map)

    def _print_scan_summary(self):
        """Print scan summary"""
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
