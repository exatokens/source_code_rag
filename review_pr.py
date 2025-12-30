"""
PR Review Entry Point
Review GitHub Pull Requests with semantic context and LLM analysis
"""
import os
import argparse
from dotenv import load_dotenv
from src.pr_review.pr_reviewer import PRReviewer
from src.llm_integration.llm_client import LLMConfig

# Load environment variables from .env file
load_dotenv()

# Import after load_dotenv to ensure env vars are loaded
import os


def main():
    """Main entry point for PR review"""

    parser = argparse.ArgumentParser(description='Review GitHub Pull Request with LLM')
    parser.add_argument('pr_url', help='GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)')
    parser.add_argument('--repo-path', required=True, help='Path to local repository')
    parser.add_argument('--llm-provider', default='groq', choices=['groq', 'openai', 'anthropic', 'local'],
                        help='LLM provider to use (default: groq)')
    parser.add_argument('--llm-model', help='LLM model name')
    parser.add_argument('--api-key', help='API key for LLM provider (or set in .env file)')
    parser.add_argument('--github-token', help='GitHub personal access token (for private repos)')
    parser.add_argument('--max-tokens', type=int, default=8000, help='Max tokens for context')
    parser.add_argument('--temperature', type=float, default=1.0, help='LLM temperature (0-2)')

    args = parser.parse_args()

    # Determine model based on provider
    if args.llm_model:
        model = args.llm_model
    else:
        if args.llm_provider == 'groq':
            model = 'openai/gpt-oss-120b'
        elif args.llm_provider == 'openai':
            model = 'gpt-4-turbo-preview'
        elif args.llm_provider == 'anthropic':
            model = 'claude-3-opus-20240229'
        else:
            model = 'llama2'  # For local

    # Create LLM config
    llm_config = LLMConfig(
        provider=args.llm_provider,
        model=model,
        api_key=args.api_key,
        temperature=args.temperature,
        max_tokens=8192,  # For LLM response
        reasoning_effort="medium"
    )

    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                      PR REVIEW WITH SEMANTIC RAG                      ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"🔧 LLM Provider: {args.llm_provider}")
    print(f"🤖 Model: {model}")
    print(f"📁 Repository: {args.repo_path}")
    print()

    # Initialize reviewer
    # Use GitHub token from args, or fall back to .env
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')

    reviewer = PRReviewer(
        repository_path=args.repo_path,
        llm_config=llm_config,
        github_token=github_token
    )

    # Review the PR
    try:
        result = reviewer.review_pr(args.pr_url, max_tokens=args.max_tokens)

        # Print summary
        reviewer.print_review_summary(result)

        print("\n✅ Review complete!")

    except Exception as e:
        print(f"\n❌ Error during review: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
