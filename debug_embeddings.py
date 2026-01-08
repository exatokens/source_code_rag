"""
Debug script to check what text was actually embedded
"""
from src.vector_store import ChromaVectorStore

# Connect to database
vector_store = ChromaVectorStore(
    persist_directory="./chroma_db",
    collection_name="code_streamlit_app"
)

# Get some auth-related documents
auth_results = vector_store.search_by_metadata(
    filters={"filepath": "utils/auth_service.py"},
    limit=3
)

print(f"\n📋 Checking what was embedded for auth functions:")
print(f"="*60)

if auth_results['ids']:
    for i, (id, metadata, document) in enumerate(zip(
        auth_results['ids'],
        auth_results['metadatas'],
        auth_results.get('documents', [])
    ), 1):
        print(f"\n{i}. {metadata.get('qualified_name', 'unknown')}")
        print(f"   File: {metadata.get('filepath')}")
        print(f"   Lines: {metadata.get('start_line')}-{metadata.get('end_line')}")
        print(f"\n   Embedded text (first 500 chars):")
        print(f"   {'-'*56}")
        if document:
            print(f"   {document[:500]}")
        else:
            print(f"   ⚠️  NO DOCUMENT TEXT!")
        print(f"   {'-'*56}")
else:
    print("⚠️  No auth documents found!")

print(f"\n{'='*60}\n")
