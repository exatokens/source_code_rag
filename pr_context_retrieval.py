import re
import os
from dataclasses import dataclass
from typing import List, Set, Dict
from collections import defaultdict

# ==================== LANGUAGE DETECTOR ====================

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


# ==================== DIFF DATA STRUCTURES ====================

@dataclass
class DiffHunk:
    """Represents a single changed section in a file"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]

@dataclass
class FileDiff:
    """Represents changes to a single file"""
    old_path: str
    new_path: str
    is_new_file: bool
    is_deleted_file: bool
    is_renamed: bool
    hunks: List[DiffHunk]
    language: str = None

@dataclass
class GitDiff:
    """Represents a complete git diff"""
    files: List[FileDiff]


# ==================== DIFF PARSER ====================

class DiffParser:
    """Parse git diff output"""
    
    @staticmethod
    def parse(diff_text: str) -> GitDiff:
        """Parse git diff text into structured format"""
        files = []
        current_file = None
        current_hunk = None
        
        lines = diff_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # New file diff starts with "diff --git"
            if line.startswith('diff --git'):
                # Save previous file
                if current_file and current_hunk:
                    current_file.hunks.append(current_hunk)
                if current_file:
                    files.append(current_file)
                
                # Start new file
                current_file = FileDiff(
                    old_path=None,
                    new_path=None,
                    is_new_file=False,
                    is_deleted_file=False,
                    is_renamed=False,
                    hunks=[]
                )
                current_hunk = None
            
            # Old file path
            elif line.startswith('--- '):
                if current_file:
                    path = line[4:].strip()
                    if path.startswith('a/'):
                        path = path[2:]
                    if path == '/dev/null':
                        current_file.is_new_file = True
                        path = None
                    current_file.old_path = path
            
            # New file path
            elif line.startswith('+++ '):
                if current_file:
                    path = line[4:].strip()
                    if path.startswith('b/'):
                        path = path[2:]
                    if path == '/dev/null':
                        current_file.is_deleted_file = True
                        path = None
                    current_file.new_path = path
                    
                    # Detect language
                    if path:
                        current_file.language = LanguageDetector.detect(path)
            
            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            elif line.startswith('@@'):
                # Save previous hunk
                if current_hunk and current_file:
                    current_file.hunks.append(current_hunk)
                
                # Parse hunk header
                match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2)) if match.group(2) else 1
                    new_start = int(match.group(3))
                    new_count = int(match.group(4)) if match.group(4) else 1
                    
                    current_hunk = DiffHunk(
                        old_start=old_start,
                        old_count=old_count,
                        new_start=new_start,
                        new_count=new_count,
                        lines=[]
                    )
            
            # Changed lines
            elif current_hunk is not None:
                if line.startswith(('+', '-', ' ')):
                    current_hunk.lines.append(line)
            
            i += 1
        
        # Save last file and hunk
        if current_file and current_hunk:
            current_file.hunks.append(current_hunk)
        if current_file:
            files.append(current_file)
        
        return GitDiff(files=files)


# ==================== CHANGED FUNCTION ====================

class ChangedFunction:
    """Represents a function that was modified in the diff"""
    def __init__(self, filepath, function_name, parent_class=None):
        self.filepath = filepath
        self.function_name = function_name
        self.parent_class = parent_class
        self.qualified_name = f"{parent_class}.{function_name}" if parent_class else function_name
        self.full_path = f"{filepath}::{parent_class}.{function_name}" if parent_class else f"{filepath}::{function_name}"
    
    def __repr__(self):
        return self.full_path


# ==================== DIFF ANALYZER ====================

class DiffAnalyzer:
    """Analyze diffs to find what changed"""
    
    def __init__(self, scanner):
        """
        scanner: Your MultiLanguageScanner instance
        """
        self.scanner = scanner
    
    def find_changed_functions(self, git_diff: GitDiff) -> List[ChangedFunction]:
        """Find which functions were modified in the diff"""
        changed_functions = []
        
        for file_diff in git_diff.files:
            if file_diff.is_deleted_file:
                continue
            
            filepath = file_diff.new_path
            
            # Get all functions in this file from our semantic graph
            file_nodes = [n for n in self.scanner.nodes 
                         if n.filepath == filepath and n.node_type in ['function', 'method']]
            
            # For each hunk, find which functions it touches
            for hunk in file_diff.hunks:
                # Lines affected by this hunk
                affected_lines = set(range(hunk.new_start, hunk.new_start + hunk.new_count))
                
                # Find functions that overlap with these lines
                for node in file_nodes:
                    function_lines = set(range(node.start_line, node.end_line + 1))
                    
                    # If there's any overlap, this function was changed
                    if affected_lines & function_lines:
                        changed_func = ChangedFunction(
                            filepath=filepath,
                            function_name=node.name,
                            parent_class=node.parent_class
                        )
                        
                        # Avoid duplicates
                        if not any(cf.full_path == changed_func.full_path for cf in changed_functions):
                            changed_functions.append(changed_func)
        
        return changed_functions


# ==================== FUNCTION CONTEXT ====================

@dataclass
class FunctionContext:
    """Complete context for a changed function"""
    # The changed function itself
    function_name: str
    qualified_name: str
    filepath: str
    start_line: int
    end_line: int
    parameters: List[str]
    return_type: str
    
    # What this function calls
    calls: List[Dict]
    
    # What calls this function
    called_by: List[Dict]
    
    # Related files
    related_files: Set[str]
    
    # The actual code
    function_code: str


# ==================== CONTEXT BUILDER ====================

class ContextBuilder:
    """Build comprehensive context for PR review"""
    
    def __init__(self, scanner):
        """
        scanner: Your MultiLanguageScanner instance
        """
        self.scanner = scanner
    
    def build_context(self, changed_function: ChangedFunction, depth: int = 1) -> FunctionContext:
        """
        Build context for a changed function
        
        depth: How many levels of calls to include
               1 = direct callers/callees only
               2 = callers of callers, etc.
        """
        
        # Find the node in our graph
        node = self.scanner.node_map.get(changed_function.full_path)
        if not node:
            print(f"Warning: Could not find {changed_function.full_path} in graph")
            return None
        
        context = FunctionContext(
            function_name=node.name,
            qualified_name=node.qualified_name,
            filepath=node.filepath,
            start_line=node.start_line,
            end_line=node.end_line,
            parameters=node.parameters,
            return_type=node.return_type if hasattr(node, 'return_type') else None,
            calls=[],
            called_by=[],
            related_files=set(),
            function_code=self._get_function_code(node)
        )
        
        # Get functions this calls (callees)
        for callee_path in node.calls:
            if callee_path in self.scanner.node_map:
                callee_node = self.scanner.node_map[callee_path]
                context.calls.append({
                    'name': callee_node.name,
                    'qualified_name': callee_node.qualified_name,
                    'filepath': callee_node.filepath,
                    'start_line': callee_node.start_line,
                    'end_line': callee_node.end_line,
                    'code': self._get_function_code(callee_node)
                })
                context.related_files.add(callee_node.filepath)
        
        # Get functions that call this (callers)
        for caller_path in node.called_by:
            if caller_path in self.scanner.node_map:
                caller_node = self.scanner.node_map[caller_path]
                context.called_by.append({
                    'name': caller_node.name,
                    'qualified_name': caller_node.qualified_name,
                    'filepath': caller_node.filepath,
                    'start_line': caller_node.start_line,
                    'end_line': caller_node.end_line,
                    'code': self._get_function_code(caller_node)
                })
                context.related_files.add(caller_node.filepath)
        
        return context
    
    def _get_function_code(self, node) -> str:
        """Extract the actual code for a function"""
        try:
            # Construct full path - node.filepath is relative from repo scan
            # We need to find the actual file
            filepath = node.filepath
            
            # If filepath doesn't exist, it might be relative to where we scanned
            if not os.path.exists(filepath):
                # Try to find it
                print(f"Warning: Could not find file {filepath}")
                return f"// File not found: {filepath}"
            
            # Read the file
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Extract the function lines
            if node.start_line <= len(lines):
                function_lines = lines[node.start_line - 1:node.end_line]
                return ''.join(function_lines)
            else:
                return f"// Line numbers out of range"
        
        except Exception as e:
            return f"// Error reading code: {e}"
    
    def build_pr_context(self, git_diff: GitDiff) -> Dict[str, FunctionContext]:
        """Build context for all changed functions in a PR"""
        
        # Find all changed functions
        analyzer = DiffAnalyzer(self.scanner)
        changed_functions = analyzer.find_changed_functions(git_diff)
        
        print(f"\nFound {len(changed_functions)} changed functions")
        
        # Build context for each
        contexts = {}
        for changed_func in changed_functions:
            print(f"  Building context for: {changed_func.full_path}")
            context = self.build_context(changed_func)
            if context:
                contexts[changed_func.full_path] = context
        
        return contexts
    
    def format_context_for_llm(self, context: FunctionContext) -> str:
        """Format context in a way that's easy for LLM to understand"""
        
        output = []
        output.append("="*70)
        output.append(f"CHANGED FUNCTION: {context.qualified_name}")
        output.append("="*70)
        output.append(f"Location: {context.filepath}:{context.start_line}")
        output.append(f"Parameters: {', '.join(context.parameters)}")
        if context.return_type:
            output.append(f"Return Type: {context.return_type}")
        
        output.append("\n--- FUNCTION CODE ---")
        output.append(context.function_code)
        
        # Functions this calls
        if context.calls:
            output.append("\n--- FUNCTIONS IT CALLS ---")
            for callee in context.calls:
                output.append(f"\n{callee['qualified_name']} ({callee['filepath']}:{callee['start_line']}):")
                output.append(callee['code'])
        
        # Functions that call this
        if context.called_by:
            output.append("\n--- FUNCTIONS THAT CALL THIS ---")
            for caller in context.called_by:
                output.append(f"\n{caller['qualified_name']} ({caller['filepath']}:{caller['start_line']}):")
                output.append(caller['code'])
        
        # Related files
        if context.related_files:
            output.append("\n--- RELATED FILES ---")
            for filepath in sorted(context.related_files):
                output.append(f"  - {filepath}")
        
        output.append("\n" + "="*70)
        
        return '\n'.join(output)


# ==================== PR CONTEXT RETRIEVER ====================

class PRContextRetriever:
    """Complete system for retrieving context from PRs"""
    
    def __init__(self, scanner):
        """
        scanner: Your MultiLanguageScanner instance
        """
        self.scanner = scanner
        self.context_builder = ContextBuilder(scanner)
    
    def analyze_pr(self, diff_text: str) -> Dict:
        """
        Analyze a PR diff and return comprehensive context
        
        Returns:
            {
                'changed_files': [...],
                'changed_functions': [...],
                'contexts': {func_path: FunctionContext, ...},
                'summary': {...}
            }
        """
        
        print("="*70)
        print("ANALYZING PR DIFF")
        print("="*70)
        
        # Parse diff
        parser = DiffParser()
        git_diff = parser.parse(diff_text)
        
        print(f"\nChanged files: {len(git_diff.files)}")
        for file_diff in git_diff.files:
            status = "NEW" if file_diff.is_new_file else "DELETED" if file_diff.is_deleted_file else "MODIFIED"
            print(f"  [{status}] {file_diff.new_path or file_diff.old_path}")
        
        # Find changed functions
        analyzer = DiffAnalyzer(self.scanner)
        changed_functions = analyzer.find_changed_functions(git_diff)
        
        print(f"\nChanged functions: {len(changed_functions)}")
        for func in changed_functions:
            print(f"  - {func.full_path}")
        
        # Build context for each changed function
        print("\nBuilding context...")
        contexts = {}
        for changed_func in changed_functions:
            context = self.context_builder.build_context(changed_func)
            if context:
                contexts[changed_func.full_path] = context
        
        # Build summary
        summary = {
            'total_changed_files': len(git_diff.files),
            'total_changed_functions': len(changed_functions),
            'languages': set(f.language for f in git_diff.files if f.language),
            'files_by_language': {},
            'impact_analysis': self._analyze_impact(contexts)
        }
        
        return {
            'changed_files': git_diff.files,
            'changed_functions': changed_functions,
            'contexts': contexts,
            'summary': summary
        }
    
    def _analyze_impact(self, contexts: Dict[str, FunctionContext]) -> Dict:
        """Analyze the impact of changes"""
        
        total_callers = 0
        total_callees = 0
        high_impact_functions = []
        
        for func_path, context in contexts.items():
            num_callers = len(context.called_by)
            num_callees = len(context.calls)
            
            total_callers += num_callers
            total_callees += num_callees
            
            # High impact if many functions call this
            if num_callers > 5:
                high_impact_functions.append({
                    'function': context.qualified_name,
                    'callers': num_callers
                })
        
        return {
            'total_callers': total_callers,
            'total_callees': total_callees,
            'high_impact_functions': high_impact_functions,
            'risk_level': 'HIGH' if high_impact_functions else 'MEDIUM' if total_callers > 3 else 'LOW'
        }
    
    def generate_review_prompt(self, pr_analysis: Dict) -> str:
        """Generate a prompt for LLM to review the PR"""
        
        prompt_parts = []
        prompt_parts.append("Please review this Pull Request.\n")
        
        # Summary
        summary = pr_analysis['summary']
        prompt_parts.append(f"Changed {summary['total_changed_functions']} functions across {summary['total_changed_files']} files.")
        prompt_parts.append(f"Languages: {', '.join(summary['languages'])}")
        prompt_parts.append(f"Risk Level: {summary['impact_analysis']['risk_level']}\n")
        
        # High impact warning
        if summary['impact_analysis']['high_impact_functions']:
            prompt_parts.append("⚠️  HIGH IMPACT CHANGES:")
            for func_info in summary['impact_analysis']['high_impact_functions']:
                prompt_parts.append(f"  - {func_info['function']} is called by {func_info['callers']} functions")
            prompt_parts.append("")
        
        # Context for each changed function
        for func_path, context in pr_analysis['contexts'].items():
            formatted = self.context_builder.format_context_for_llm(context)
            prompt_parts.append(formatted)
        
        prompt_parts.append("\nPlease analyze:")
        prompt_parts.append("1. Are there any bugs or logic errors?")
        prompt_parts.append("2. Are there potential breaking changes?")
        prompt_parts.append("3. Is error handling adequate?")
        prompt_parts.append("4. Are there performance concerns?")
        prompt_parts.append("5. Does it follow best practices?")
        
        return '\n'.join(prompt_parts)
    
    def save_context(self, pr_analysis: Dict, output_file: str = 'pr_review_context.txt'):
        """Save the PR context to a file"""
        review_prompt = self.generate_review_prompt(pr_analysis)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(review_prompt)
        
        print(f"\n✓ Context saved to {output_file}")
        print(f"✓ Total size: {len(review_prompt)} characters")
        print(f"✓ Ready to send to LLM")


# ==================== MAIN EXAMPLE ====================

if __name__ == "__main__":
    # Example usage - you'll need to import your scanner
    
    # TEST WITH SAMPLE DIFF
    sample_diff = """
diff --git a/src/utils/auth_service.py b/src/utils/auth_service.py
index 1234567..abcdefg 100644
--- a/src/utils/auth_service.py
+++ b/src/utils/auth_service.py
@@ -70,7 +70,8 @@ class AuthService:
     @staticmethod
     def authenticate_user(username, password):
         \"\"\"Authenticate user with username and password\"\"\"
-        if username in ALLOWED_USERS and ALLOWED_USERS[username] == password:
+        # Added input validation
+        if username and username in ALLOWED_USERS and ALLOWED_USERS[username] == password:
             return True
         return False
"""
    
    print("Testing Diff Parser...")
    parser = DiffParser()
    git_diff = parser.parse(sample_diff)
    
    print(f"\n✓ Parsed {len(git_diff.files)} files")
    for file_diff in git_diff.files:
        print(f"  - {file_diff.new_path} ({file_diff.language})")
        print(f"    Hunks: {len(file_diff.hunks)}")
        for hunk in file_diff.hunks:
            print(f"      Lines {hunk.new_start}-{hunk.new_start + hunk.new_count - 1}")
            print(f"      Changed lines: {len(hunk.lines)}")
    
    print("\n" + "="*70)
    print("To use with your scanner:")
    print("="*70)
    print("""
from semantic_tree_builder import MultiLanguageScanner
from pr_context_retrieval import PRContextRetriever

# 1. Scan your repository
scanner = MultiLanguageScanner()
scanner.scan_repository('/path/to/your/repo')

# 2. Analyze a PR
retriever = PRContextRetriever(scanner)
pr_analysis = retriever.analyze_pr(diff_text)

# 3. Save context for LLM
retriever.save_context(pr_analysis, 'pr_review.txt')
    """)