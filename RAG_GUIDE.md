# Repository RAG System - Complete Guide

## 🎯 Overview

A complete Retrieval-Augmented Generation (RAG) system for GitHub repositories that enables natural language querying of codebases.

**What it does:**
- Index entire repositories (language-agnostic)
- Answer questions about code using natural language
- Combine semantic search with code structure understanding
- Generate context-aware answers using LLMs

## 🏗️ Architecture

```
User Question: "How does authentication work?"
       ↓
[1. Embed Question] (sentence-transformers)
       ↓
[2. Vector Search] (ChromaDB) → Top-K similar functions
       ↓
[3. Semantic Expansion] (Call graph) → Add callers/callees
       ↓
[4. Context Assembly] → Rich code context
       ↓
[5. LLM Generation] (Groq/OpenAI) → Natural language answer
```

## 📦 Components

### 1. **Embedding System** ([src/embeddings/](src/embeddings/))
- **embedding_generator.py**: Generate 384-dim vectors using `all-MiniLM-L6-v2`
- **code_preprocessor.py**: Clean and prepare code for embedding
- **chunk_strategy.py**: Define granularity (function/class/file level)

### 2. **Vector Store** ([src/vector_store/](src/vector_store/))
- **chroma_store.py**: ChromaDB integration for fast similarity search
- **indexer.py**: Index entire repositories
- **retriever.py**: Hybrid search (vector + semantic tree)

### 3. **Semantic Tree** (existing)
- **semantic_tree_builder.py**: Parse code with tree-sitter
- **src/extractors/**: Multi-language extractors
- **src/utils/call_graph_builder.py**: Build function call graph

### 4. **Main Interface**
- **repo_rag.py**: Complete RAG system interface

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
pip install -r requirements_rag.txt
```

**New dependencies:**
- `sentence-transformers` - Generate embeddings locally
- `chromadb` - Vector database
- `numpy` - Vector operations

### Step 2: Index a Repository

```bash
# Index current repository
python repo_rag.py index .

# Index external repository
python repo_rag.py index /path/to/repo --granularity function

# Force rebuild existing index
python repo_rag.py index . --force-rebuild
```

**Indexing process:**
1. Parse code → Semantic tree (tree-sitter)
2. Generate embeddings → 384-dim vectors (sentence-transformers)
3. Store in ChromaDB → Fast similarity search

### Step 3: Query the Repository

```bash
# Single query
python repo_rag.py query "How does authentication work?" --repo-path .

# Query without LLM (just show context)
python repo_rag.py query "How are errors handled?" --repo-path . --no-llm

# Filter by language
python repo_rag.py query "How is data validated?" --repo-path . --language python
```

### Step 4: Interactive Mode

```bash
python repo_rag.py interactive .
```

Then ask questions:
```
❓ Your question: How does PR review work?
❓ Your question: What functions handle authentication?
❓ Your question: quit
```

## 💻 Programmatic Usage

### Basic Usage

```python
from repo_rag import RepoRAG

# Initialize
rag = RepoRAG(repository_path="/path/to/repo")

# Index (one-time)
rag.index(granularity="function")

# Query
result = rag.query("How does user login work?")
print(result['answer'])
```

### Advanced Usage

```python
# Custom collection name
rag = RepoRAG(
    repository_path="/path/to/repo",
    collection_name="my_custom_index",
    persist_directory="./my_vector_db"
)

# Index with specific granularity
rag.index(
    granularity="function",  # or "class", "file"
    force_rebuild=False
)

# Query with options
result = rag.query(
    question="How is data cached?",
    top_k=10,              # More initial results
    use_llm=True,          # Generate answer
    language_filter="python"  # Only Python code
)

# Access raw context
for ctx in result['context']:
    print(f"{ctx['metadata']['qualified_name']}: {ctx['location']}")
```

### Multiple Queries

```python
questions = [
    "How is authentication handled?",
    "What database operations exist?",
    "How are errors logged?"
]

for question in questions:
    result = rag.query(question, top_k=5)
    print(f"Q: {question}")
    print(f"A: {result['answer']}\n")
```

## 🔧 Configuration Options

### Chunking Strategies

**Function-level (RECOMMENDED)**
```python
rag.index(granularity="function")
```
- Each function/method is a separate searchable unit
- Best for most questions
- ~500-1000 chunks per 10K LOC

**Class-level**
```python
rag.index(granularity="class")
```
- Entire classes as single units
- Good for OOP-heavy codebases
- Fewer chunks, more context per chunk

**File-level**
```python
rag.index(granularity="file")
```
- Whole files as units
- Use for small files or module-level questions
- Largest context windows

### Retrieval Parameters

```python
result = rag.query(
    question="...",
    top_k=5,                    # Initial vector search results
    use_llm=True,               # Generate answer vs just context
    language_filter="python"    # Filter by language
)
```

### Storage Locations

```python
rag = RepoRAG(
    repository_path="/path/to/repo",
    collection_name="my_index",           # Collection name
    persist_directory="./custom_db_path"  # Where to store ChromaDB
)
```

## 📊 How It Works

### 1. Indexing Phase

```
Repository Files
    ↓
[Tree-sitter Parse] → AST for each file
    ↓
[Extract Nodes] → Functions, classes, methods
    ↓
[Build Call Graph] → Who calls what?
    ↓
[Generate Embeddings] → 384-dim vectors
    ↓
[Store in ChromaDB] → Fast vector search
```

**What gets indexed:**
- Functions and methods
- Classes
- Parameters and return types
- Docstrings
- Call relationships
- File locations

### 2. Query Phase

```
User Question: "How does caching work?"
    ↓
[Embed Question] → 384-dim vector
    ↓
[Vector Search] → Find similar code (cosine similarity)
    ↓
    Results:
    1. cache_get() - 92% match
    2. cache_set() - 89% match
    3. invalidate_cache() - 85% match
    ↓
[Semantic Expansion]
    For each result, add:
    - Functions that call it (impact)
    - Functions it calls (dependencies)
    - Related tests
    ↓
[Format Context] → Markdown with code blocks
    ↓
[LLM Generation] → Natural language answer
```

### 3. Hybrid Retrieval

**Why hybrid is powerful:**

Vector search alone:
```python
# Finds semantically similar code
query: "How is data validated?"
→ validate_user_input()
→ check_email_format()
```

Hybrid (vector + semantic tree):
```python
# Finds similar code + related context
query: "How is data validated?"
→ validate_user_input()           [vector match]
  → process_form()                [caller - shows usage]
  → sanitize_input()              [callee - shows implementation]
  → test_validation()             [test - shows expected behavior]
```

## 🎯 Example Use Cases

### 1. Understanding New Codebases

```python
# "How does the app start?"
# "What's the main entry point?"
# "How is configuration loaded?"
```

### 2. Feature Location

```python
# "Where is user authentication implemented?"
# "How are payments processed?"
# "Where is data validation done?"
```

### 3. Impact Analysis

```python
# "What functions use the database connection?"
# "What depends on the User class?"
# "Where is the API key used?"
```

### 4. Code Review Assistance

```python
# "How should I implement caching?"
# "What's the pattern for error handling?"
# "How are similar features tested?"
```

## 📈 Performance

### Indexing Speed
- **Small repo** (< 100 files): ~30 seconds
- **Medium repo** (100-1000 files): ~2-5 minutes
- **Large repo** (> 1000 files): ~10-30 minutes

**One-time cost** - subsequent queries are fast!

### Query Speed
- Vector search: **< 100ms**
- Semantic expansion: **< 200ms**
- LLM generation: **2-5 seconds** (depends on LLM)

**Total query time: ~3-5 seconds**

### Storage Requirements
- Embeddings: ~1.5 KB per function (384 dims × 4 bytes)
- 10,000 functions ≈ **15 MB**
- ChromaDB overhead: ~2× (metadata, indices)
- **Total: ~30-50 MB for 10K functions**

## 🔍 Advanced Features

### Language Filtering

```python
# Only search Python code
result = rag.query("How is logging done?", language_filter="python")

# Only search Java code
result = rag.query("How is logging done?", language_filter="java")
```

### Check Index Stats

```python
stats = rag.get_stats()
print(f"Total indexed: {stats['total_documents']}")
print(f"Languages: {stats['languages']}")
print(f"Node types: {stats['node_types']}")
```

### Rebuild Index

```python
# Force complete rebuild
rag.index(force_rebuild=True)
```

## 🛠️ Customization

### Use Different Embedding Model

Edit [src/embeddings/embedding_generator.py](src/embeddings/embedding_generator.py):

```python
# Option 1: Larger model (better quality, slower)
generator = EmbeddingGenerator(model_name='all-mpnet-base-v2')

# Option 2: Code-specific model
generator = EmbeddingGenerator(model_name='microsoft/codebert-base')
```

### Use Different LLM

The system uses your existing LLM configuration (`.env` with `GROQ_API_KEY`).

To use a different provider, modify [src/llm_integration/llm_client.py](src/llm_integration/llm_client.py).

### Adjust Context Size

Edit [repo_rag.py](repo_rag.py):

```python
# More context items (slower, more thorough)
retrieval_result = self.retriever.retrieve(
    question=question,
    top_k=10,              # More vector results
    max_context_items=30   # More total items
)
```

## 🐛 Troubleshooting

### "No results found"
- Check if repository is indexed: `python repo_rag.py stats`
- Rebuild index: `python repo_rag.py index . --force-rebuild`
- Try broader question: "authentication" → "How does login work?"

### "Model download failed"
- First run downloads ~80MB model from HuggingFace
- Requires internet connection
- Model cached in `~/.cache/torch/sentence_transformers/`

### "Out of memory"
- Reduce batch size in `embedding_generator.py`: `batch_size=16`
- Use class-level granularity instead of function-level
- Process repository in chunks

## 📚 Next Steps

1. **Try it**: Run `example_rag_usage.py`
2. **Index your repo**: `python repo_rag.py index .`
3. **Ask questions**: `python repo_rag.py interactive .`
4. **Customize**: Adjust chunking, embedding models, LLMs

## 🔗 Related Files

- **[README.md](README.md)** - Main project documentation
- **[PR_REVIEW_GUIDE.md](PR_REVIEW_GUIDE.md)** - PR review feature
- **[example_rag_usage.py](example_rag_usage.py)** - Usage examples
