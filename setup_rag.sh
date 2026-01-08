#!/bin/bash

# Setup script for Repository RAG system

echo "======================================"
echo "🚀 Setting up Repository RAG System"
echo "======================================"

# Check Python version
echo ""
echo "📋 Checking Python version..."
python --version

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements_rag.txt

# Verify installations
echo ""
echo "✅ Verifying installations..."

python -c "import sentence_transformers; print('✓ sentence-transformers installed')"
python -c "import chromadb; print('✓ chromadb installed')"
python -c "import numpy; print('✓ numpy installed')"

echo ""
echo "======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Index a repository:"
echo "   python repo_rag.py index /path/to/repo"
echo ""
echo "2. Query it:"
echo "   python repo_rag.py query 'How does X work?' --repo-path /path/to/repo"
echo ""
echo "3. Interactive mode:"
echo "   python repo_rag.py interactive /path/to/repo"
echo ""
echo "See RAG_GUIDE.md for complete documentation"
echo ""
