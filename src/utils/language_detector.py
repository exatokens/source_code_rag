"""
Language detection utility for source files
"""
import os


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
        """
        Detect language from file extension

        Args:
            filepath: Path to the source file

        Returns:
            Language identifier (str) or None if not supported
        """
        _, ext = os.path.splitext(filepath)
        return LanguageDetector.LANGUAGE_MAP.get(ext.lower())
