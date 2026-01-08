# RAG System - Quick Reference Cheatsheet

## 🚀 Quick Start (3 Steps)

```bash
# 1. Install
pip install sentence-transformers chromadb numpy

# 2. Index your repository
python repo_rag.py index /path/to/repo

# 3. Query it
python repo_rag.py query "How does X work?" --repo-path /path/to/repo
```

## 📋 CLI Commands

### Index Repository
```bash
# Index current directory
python repo_rag.py index .

# Index specific repo
python repo_rag.py index /path/to/repo

# Force rebuild
python repo_rag.py index . --force-rebuild

# Use class-level chunking
python repo_rag.py index . --granularity class
```

### Query
```bash
# Basic query
python repo_rag.py query "How does auth work?" --repo-path .

# Without LLM (just show context)
python repo_rag.py query "How does auth work?" --repo-path . --no-llm

# Filter by language
python repo_rag.py query "How is data validated?" --repo-path . --language python
```

### Interactive Mode
```bash
python repo_rag.py interactive /path/to/repo
```

### Stats
```bash
python repo_rag.py stats --path-or-query /path/to/repo
```

## 💻 Python API

### Basic Usage
```python
from repo_rag import RepoRAG

# Initialize
rag = RepoRAG("/path/to/repo")

# Index
rag.index()

# Query
result = rag.query("How does X work?")
print(result['answer'])
```

### Advanced Configuration
```python
# Custom setup
rag = RepoRAG(
    repository_path="/path/to/repo",
    collection_name="my_index",
    persist_directory="./my_db"
)

# Index with options
rag.index(
    granularity="function",  # or "class", "file"
    force_rebuild=False
)

# Query with options
result = rag.query(
    question="How does caching work?",
    top_k=10,                   # More results
    use_llm=True,               # Generate answer
    language_filter="python"    # Filter language
)
```

### Access Raw Results
```python
result = rag.query("How does X work?")

# Answer
print(result['answer'])

# Context chunks
for ctx in result['context']:
    print(f"{ctx['metadata']['qualified_name']}")
    print(f"  Location: {ctx['location']}")
    print(f"  Code:\n{ctx['code']}\n")

# Formatted context (what was sent to LLM)
print(result['formatted_context'])
```

### Multiple Queries
```python
questions = [
    "How is authentication done?",
    "Where is data validated?",
    "How are errors handled?"
]

for q in questions:
    result = rag.query(q, top_k=5)
    print(f"\nQ: {q}")
    print(f"A: {result['answer']}")
```

### Interactive Mode
```python
rag = RepoRAG("/path/to/repo")
rag.interactive()  # Enter interactive Q&A
```

### Get Stats
```python
stats = rag.get_stats()
print(f"Total: {stats['total_documents']}")
print(f"Languages: {stats['languages']}")
print(f"Types: {stats['node_types']}")
```

## 🎯 Common Use Cases

### Understanding Code
```python
"How does the application start?"
"What's the main entry point?"
"How is configuration loaded?"
"How does the routing work?"
```

### Finding Features
```python
"Where is user authentication implemented?"
"How are payments processed?"
"Where is data validation done?"
"How is logging implemented?"
```

### Impact Analysis
```python
"What functions use the database?"
"What depends on the User class?"
"Where is the API key used?"
"What calls send_email()?"
```

### Pattern Discovery
```python
"How are errors handled?"
"What's the testing pattern?"
"How is caching implemented?"
"What's the authentication flow?"
```

## ⚙️ Configuration

### Chunking Granularity
```python
# Function-level (RECOMMENDED) - most questions
rag.index(granularity="function")

# Class-level - OOP-heavy code
rag.index(granularity="class")

# File-level - module questions
rag.index(granularity="file")
```

### Retrieval Parameters
```python
result = rag.query(
    question="...",
    top_k=5,              # Initial vector results (default: 5)
    use_llm=True,         # Generate answer (default: True)
    language_filter=None  # Filter: "python", "java", etc.
)
```

## 🔧 Files & Structure

### Created Files
```
src/embeddings/
  ├── embedding_generator.py   # Generate embeddings
  ├── code_preprocessor.py     # Prepare code for embedding
  └── chunk_strategy.py        # Chunking strategies

src/vector_store/
  ├── chroma_store.py          # ChromaDB integration
  ├── indexer.py               # Index repositories
  └── retriever.py             # Hybrid retrieval

repo_rag.py                    # Main interface
```

### Documentation
```
RAG_GUIDE.md                   # Complete guide
RAG_IMPLEMENTATION_SUMMARY.md  # What we built
RAG_CHEATSHEET.md             # This file
example_rag_usage.py          # Code examples
```

## 🐛 Troubleshooting

### No results found
```bash
# Check if indexed
python repo_rag.py stats

# Rebuild index
python repo_rag.py index . --force-rebuild
```

### Model download failed
- First run downloads ~80MB from HuggingFace
- Requires internet connection
- Cached in `~/.cache/torch/sentence_transformers/`

### Out of memory
```python
# Edit src/embeddings/embedding_generator.py
# Reduce batch_size: embed_batch(..., batch_size=16)

# Or use class-level granularity
rag.index(granularity="class")
```

## 📊 Performance

| Operation | Time |
|-----------|------|
| Indexing 10K functions | 2-5 min |
| Vector search | < 100ms |
| Semantic expansion | < 200ms |
| LLM generation | 2-5 sec |
| **Total query** | **3-5 sec** |

## 💾 Storage

| Size | Storage |
|------|---------|
| Per function | ~1.5 KB |
| 10K functions | ~30 MB |
| Database overhead | ~2× |

## 🔗 Quick Links

- Full guide: [RAG_GUIDE.md](RAG_GUIDE.md)
- Implementation details: [RAG_IMPLEMENTATION_SUMMARY.md](RAG_IMPLEMENTATION_SUMMARY.md)
- Examples: [example_rag_usage.py](example_rag_usage.py)
- Setup: `bash setup_rag.sh`

## 📝 Example Session

```bash
# Setup
$ pip install -r requirements_rag.txt
$ python repo_rag.py index .

🔄 Initializing ChromaDB...
✅ Collection 'code_source_code_rag' ready
📊 Step 1/4: Building semantic tree...
   ✅ Parsed 127 semantic nodes
📋 Step 2/4: Filtering nodes...
   Nodes to embed: 89/127
🔮 Step 3/4: Generating embeddings...
   ✅ Generated 89 embeddings
💾 Step 4/4: Storing in ChromaDB...
   ✅ Added 89 embeddings
✅ INDEXING COMPLETE

# Query
$ python repo_rag.py interactive .

❓ Your question: How does PR review work?

🔍 Retrieving context...
   📊 Vector search (top-5)...
   ✅ Found 5 vector matches
   🌳 Expanding with semantic tree...
   ✅ Expanded to 12 total items
🤖 Generating answer with LLM...

💡 Answer:
PR review in this codebase works by...
[detailed answer with code references]

❓ Your question: quit
👋 Goodbye!
```
