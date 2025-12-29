# In another file or script:
from semantic_tree_builder import MultiLanguageScanner
from pr_context_retrieval import PRContextRetriever

# 1. Scan repository
scanner = MultiLanguageScanner()
scanner.scan_repository('/Users/siva/web_developments/streamlit_app')

# 2. Get your git diff (from git command, GitHub API, or paste it)
with open('my_pr.diff', 'r') as f:
    diff_text = f.read()

# 3. Analyze PR
retriever = PRContextRetriever(scanner)
pr_analysis = retriever.analyze_pr(diff_text)

# 4. Generate and save context
retriever.save_context(pr_analysis, 'pr_review_context.txt')

# Now send pr_review_context.txt to your LLM!