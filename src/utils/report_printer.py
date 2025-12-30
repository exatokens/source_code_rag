"""
Report printing utilities for semantic analysis
"""
from collections import defaultdict


class ReportPrinter:
    """Print various reports and summaries"""

    @staticmethod
    def print_summary(stats):
        """Print a summary of the scan"""
        print("\n" + "="*70)
        print("REPOSITORY SUMMARY")
        print("="*70)
        print(f"Total Files: {stats['total_files']}")
        print(f"Total Classes: {stats['total_classes']}")
        print(f"Total Enums: {stats['total_enums']}")
        print(f"Total Interfaces: {stats['total_interfaces']}")
        print(f"Total Functions: {stats['total_functions']}")
        print(f"Total Methods: {stats['total_methods']}")

        print("\nBy Language:")
        for lang, counts in stats['by_language'].items():
            print(f"\n  {lang.upper()}:")
            print(f"    Classes: {counts['classes']}")
            print(f"    Enums: {counts['enums']}")
            print(f"    Interfaces: {counts['interfaces']}")
            print(f"    Functions: {counts['functions']}")
            print(f"    Methods: {counts['methods']}")

        print("\nTop 10 Files by Function Count:")
        sorted_files = sorted(
            stats['files'].items(),
            key=lambda x: x[1]['functions'] + x[1]['methods'],
            reverse=True
        )[:10]

        for filepath, counts in sorted_files:
            total = counts['functions'] + counts['methods']
            types = counts['classes'] + counts['enums'] + counts['interfaces']
            print(f"  {filepath}:")
            print(f"    {total} functions/methods ({counts['classes']} classes, {counts['enums']} enums, {counts['interfaces']} interfaces)")

    @staticmethod
    def print_function_details(func_name, results, node_map):
        """Print details for a specific function"""
        if not results:
            print(f"\nNo function named '{func_name}' found.")
            return

        print(f"\n{'='*70}")
        print(f"FUNCTION DETAILS: {func_name}")
        print(f"{'='*70}")

        for node in results:
            print(f"\n{node.full_path} [{node.language}]")
            print(f"  Type: {node.node_type}")
            print(f"  Lines: {node.start_line}-{node.end_line}")
            if node.parent_class:
                print(f"  Parent: {node.parent_class}")
            if node.return_type:
                print(f"  Return Type: {node.return_type}")
            print(f"  Parameters: {node.parameters}")
            print(f"  Calls: {len(node.calls)} functions")
            for call in node.calls[:10]:
                print(f"    -> {call}")
            if len(node.calls) > 10:
                print(f"    ... and {len(node.calls) - 10} more")
            print(f"  Called by: {len(node.called_by)} functions")
            for caller in node.called_by[:10]:
                print(f"    <- {caller}")
            if len(node.called_by) > 10:
                print(f"    ... and {len(node.called_by) - 10} more")

    @staticmethod
    def print_type_details(type_name, results, nodes):
        """Print details for a specific class, enum, or interface"""
        if not results:
            print(f"\nNo type named '{type_name}' found.")
            return

        for type_node in results:
            methods = [n for n in nodes if n.parent_class == type_name and n.node_type == 'method']

            print(f"\n{'='*70}")
            print(f"{type_node.node_type.upper()} DETAILS: {type_name} [{type_node.language}]")
            print(f"{'='*70}")

            print(f"\nLocation: {type_node.full_path}")
            print(f"Lines: {type_node.start_line}-{type_node.end_line}")
            print(f"Total Methods: {len(methods)}")

            if methods:
                print(f"\nMethods:")
                for method in sorted(methods, key=lambda m: m.start_line):
                    params_str = ', '.join(method.parameters) if method.parameters else ''
                    return_type_str = f" -> {method.return_type}" if method.return_type else ""
                    print(f"  • {method.name}({params_str}){return_type_str}")
                    print(f"      Line {method.start_line} | Calls: {len(method.calls)} | Called by: {len(method.called_by)}")

            if methods:
                print(f"\nMost Called Methods:")
                sorted_methods = sorted(methods, key=lambda m: len(m.called_by), reverse=True)[:5]
                for method in sorted_methods:
                    if method.called_by:
                        print(f"  • {method.name}: called {len(method.called_by)} times")
                        for caller in method.called_by[:3]:
                            print(f"      <- {caller}")
                        if len(method.called_by) > 3:
                            print(f"      ... and {len(method.called_by) - 3} more")

    @staticmethod
    def print_all_types(nodes):
        """Print all classes, enums, and interfaces"""
        types = [n for n in nodes if n.node_type in ['class', 'enum', 'interface']]

        print("\n" + "="*70)
        print("ALL TYPES (Classes, Enums, Interfaces)")
        print("="*70)

        types_by_file = defaultdict(list)
        for node in types:
            types_by_file[node.filepath].append(node)

        for filepath in sorted(types_by_file.keys()):
            print(f"\n{filepath}:")
            for node in sorted(types_by_file[filepath], key=lambda n: n.start_line):
                method_count = len([n for n in nodes if n.parent_class == node.name])
                type_label = f"[{node.node_type}]"
                print(f"  • {node.name} {type_label:12} [{node.start_line}] - {method_count} methods")
