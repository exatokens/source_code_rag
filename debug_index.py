"""
Debug script to check what's in the vector database
"""
from src.vector_store import ChromaVectorStore
from src.embeddings import EmbeddingGenerator

# Connect to existing database
vector_store = ChromaVectorStore(
    persist_directory="./chroma_db",
    collection_name="code_streamlit_app"
)

# Get stats
stats = vector_store.get_stats()
print(f"\n📊 Database Stats:")
print(f"   Total documents: {stats['total_documents']}")
print(f"   Languages: {stats['languages']}")
print(f"   Node types: {stats['node_types']}")

# Search for auth-related code
print(f"\n🔍 Searching for auth-related code by metadata...")
auth_results = vector_store.search_by_metadata(
    filters={"filepath": "utils/auth_service.py"},
    limit=10
)

print(f"\n   Found {len(auth_results['ids'])} items from auth_service.py:")
for i, (id, metadata) in enumerate(zip(auth_results['ids'], auth_results['metadatas'])):
    print(f"   {i+1}. {metadata.get('qualified_name', 'unknown')}")

# Test a query
print(f"\n🧪 Testing vector search for 'authentication'...")
generator = EmbeddingGenerator()
query_embedding = generator.embed_single("How does authentication work?")

results = vector_store.query(
    query_embedding=query_embedding,
    n_results=5
)

print(f"\n   Top 5 results:")
if results['ids'] and len(results['ids']) > 0:
    for i, (id, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['distances'][0]
    )):
        similarity = 1 - distance
        print(f"   {i+1}. {metadata.get('qualified_name', 'unknown')} - {similarity:.2%} similarity")
else:
    print("   No results found!")

print("\n" + "="*60)
