"""
Main entry point for semantic tree builder
Language-agnostic code repository analysis tool
"""
from src.parsers.repository_scanner import RepositoryScanner
from src.utils.call_graph_builder import CallGraphBuilder
from src.utils.node_search import NodeSearch
from src.utils.report_printer import ReportPrinter


def main():
    """Main function to run the semantic tree builder"""

    # Initialize scanner
    scanner = RepositoryScanner()

    # Repository path
    repo_path = '/Users/siva/web_developments/streamlit_app'

    # Scan repository
    nodes = scanner.scan_repository(repo_path)

    # Build call graph
    CallGraphBuilder.build_call_graph(nodes, scanner.node_map)

    # Get statistics
    stats = scanner.get_statistics()

    # Print summary
    ReportPrinter.print_summary(stats)

    # Example queries (uncomment to use):
    # ReportPrinter.print_type_details('KafkaProperties', NodeSearch.search_type(nodes, 'KafkaProperties'), nodes)
    # ReportPrinter.print_all_types(nodes)


if __name__ == "__main__":
    main()
