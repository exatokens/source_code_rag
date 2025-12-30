"""
Parse unified diff format to extract changed code
"""
import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class HunkChange:
    """Represents a single hunk (change block) in a diff"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]  # Lines in this hunk (with +/- prefix)


@dataclass
class FileChange:
    """Represents changes to a single file"""
    filepath: str
    old_filepath: str
    status: str  # 'modified', 'added', 'deleted', 'renamed'
    hunks: List[HunkChange]
    added_lines: List[Tuple[int, str]]  # (line_number, content)
    removed_lines: List[Tuple[int, str]]  # (line_number, content)
    modified_ranges: List[Tuple[int, int]]  # (start_line, end_line) ranges that changed


class DiffParser:
    """Parse unified diff format"""

    @staticmethod
    def parse_diff(diff_content: str) -> List[FileChange]:
        """
        Parse unified diff content

        Args:
            diff_content: Raw diff content

        Returns:
            List of FileChange objects
        """
        file_changes = []
        current_file = None
        current_hunk = None

        lines = diff_content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # New file starts with "diff --git"
            if line.startswith('diff --git'):
                if current_file:
                    file_changes.append(current_file)

                # Parse file paths
                match = re.match(r'diff --git a/(.*) b/(.*)', line)
                if match:
                    old_path = match.group(1)
                    new_path = match.group(2)

                    current_file = FileChange(
                        filepath=new_path,
                        old_filepath=old_path,
                        status='modified',
                        hunks=[],
                        added_lines=[],
                        removed_lines=[],
                        modified_ranges=[]
                    )

            # File status (new file, deleted file, etc.)
            elif line.startswith('new file'):
                if current_file:
                    current_file.status = 'added'
            elif line.startswith('deleted file'):
                if current_file:
                    current_file.status = 'deleted'
            elif line.startswith('rename from'):
                if current_file:
                    current_file.status = 'renamed'

            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            elif line.startswith('@@'):
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2)) if match.group(2) else 1
                    new_start = int(match.group(3))
                    new_count = int(match.group(4)) if match.group(4) else 1

                    current_hunk = HunkChange(
                        old_start=old_start,
                        old_count=old_count,
                        new_start=new_start,
                        new_count=new_count,
                        lines=[]
                    )

                    if current_file:
                        current_file.hunks.append(current_hunk)

            # Content lines within a hunk
            elif current_hunk is not None:
                if line.startswith('+') and not line.startswith('+++'):
                    # Added line
                    current_hunk.lines.append(line)
                    if current_file:
                        # Calculate line number in new file
                        line_num = current_hunk.new_start + len([l for l in current_hunk.lines if l.startswith('+') or l.startswith(' ')]) - 1
                        current_file.added_lines.append((line_num, line[1:]))  # Remove + prefix

                elif line.startswith('-') and not line.startswith('---'):
                    # Removed line
                    current_hunk.lines.append(line)
                    if current_file:
                        line_num = current_hunk.old_start + len([l for l in current_hunk.lines if l.startswith('-') or l.startswith(' ')]) - 1
                        current_file.removed_lines.append((line_num, line[1:]))  # Remove - prefix

                elif line.startswith(' '):
                    # Context line (unchanged)
                    current_hunk.lines.append(line)

            i += 1

        # Don't forget the last file
        if current_file:
            file_changes.append(current_file)

        # Calculate modified ranges for each file
        for file_change in file_changes:
            file_change.modified_ranges = DiffParser._calculate_modified_ranges(file_change)

        return file_changes

    @staticmethod
    def _calculate_modified_ranges(file_change: FileChange) -> List[Tuple[int, int]]:
        """
        Calculate line ranges that were modified in the new version

        Args:
            file_change: FileChange object

        Returns:
            List of (start_line, end_line) tuples
        """
        ranges = []

        for hunk in file_change.hunks:
            start_line = hunk.new_start
            end_line = hunk.new_start + hunk.new_count - 1
            ranges.append((start_line, end_line))

        return ranges

    @staticmethod
    def get_changed_functions(file_change: FileChange, semantic_nodes: list) -> list:
        """
        Get semantic nodes (functions/methods) that were modified

        Args:
            file_change: FileChange object
            semantic_nodes: List of SemanticNode objects for this file

        Returns:
            List of SemanticNode objects that have actual code changes (not just context)
        """
        # Get actual changed line numbers (only added/removed lines, not context)
        changed_line_numbers = set()
        for line_num, _ in file_change.added_lines:
            changed_line_numbers.add(line_num)
        for line_num, _ in file_change.removed_lines:
            changed_line_numbers.add(line_num)

        # Use a dict to deduplicate nodes by their full_path
        changed_nodes_dict = {}

        for node in semantic_nodes:
            # Check if node is in the same file
            if node.filepath != file_change.filepath:
                continue

            # Skip if already added
            if node.full_path in changed_nodes_dict:
                continue

            # Check if any actual changed line falls within this node's range
            node_has_changes = any(
                node.start_line <= line_num <= node.end_line
                for line_num in changed_line_numbers
            )

            if node_has_changes:
                changed_nodes_dict[node.full_path] = node

        return list(changed_nodes_dict.values())

    @staticmethod
    def _ranges_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
        """Check if two line ranges overlap"""
        return start1 <= end2 and start2 <= end1
