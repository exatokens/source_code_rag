the goal of this project is to create a search system where user can ask questions for a given repo. for this we are building a rag for a given github or bitbucket repo. and we can also configure the llm. so when we ask a question we get the closest code for the question, retrieve all the functions , classes or any sources related to that and feed it to llm to get generative answers. this should be language agnostic.


A code-aware retrieval system that maps natural-language questions → semantic code units → structured context → LLM reasoning


Building the Semantic Tree - Deep Dive
Step 1: Parse Code into AST (Abstract Syntax Tree)
What we need:

Tree-sitter (multi-language parser)
Language Server Protocol (LSP) adapters (optional, for IDE-level understanding)

What we extract:

```
# For each file, build nodes:
{
  "file": "src/checkout.py",
  "language": "python",
  "nodes": [
    {
      "type": "class",
      "name": "ShoppingCart",
      "line_start": 10,
      "line_end": 45,
      "methods": [...],
      "attributes": [...],
      "decorators": [...],
      "parent_class": "BaseCart"
    },
    {
      "type": "function", 
      "name": "calculatePrice",
      "line_start": 20,
      "line_end": 30,
      "parameters": ["items", "discount"],
      "return_type": "float",
      "calls": ["getTax", "applyDiscount"],  # Functions it calls
      "called_by": [],  # Filled by dependency analysis
      "variables_used": ["TAX_RATE", "self.currency"]
    }
  ]
}
```

**Why tree-sitter:**
- Supports 50+ languages with same API
- Incremental parsing (fast updates)
- Error-tolerant (works with incomplete code)

---

### Step 2: Build Dependency Graph

**What we need:**
- **Symbol resolver** - matches function calls to definitions
- **Import analyzer** - tracks cross-file dependencies
- **Graph database** (Neo4j) or in-memory graph structure

**Graph structure:**
```
Nodes:
- Files
- Classes  
- Functions
- Variables/Constants
- Imports

Edges:
- CONTAINS (file contains class)
- DEFINES (class defines method)
- CALLS (function calls function)
- USES (function uses variable)
- IMPORTS (file imports module)
- INHERITS (class inherits class)
- IMPLEMENTS (class implements interface)
- TESTS (test file tests source file)
```

**Example graph for our PR:**
```
checkout.py 
  ├─ ShoppingCart (class)
  │   ├─ __init__
  │   ├─ calculatePrice  ← CHANGED IN PR
  │   │   ├─ CALLS → getTax
  │   │   ├─ CALLS → applyDiscount  
  │   │   ├─ USES → TAX_RATE
  │   │   └─ CALLED_BY → [processOrder, handleCheckout]
  │   └─ addItem
  │
  └─ IMPORTS → tax_calculator.py
  └─ TESTED_BY → test_checkout.py

```

Step 3: Dynamic Context Retrieval for Changed Code

When PR modifies calculatePrice(), we dynamically build context:
#### Level 1 - Direct Context (always include):

```
# The changed function itself
def calculatePrice(self, items, discount):
    # changed code
    
# Its immediate callers (who will be affected)
def processOrder(self):
    price = self.calculatePrice(...)  # This might break!
    
# Its immediate callees (dependencies)
def getTax(amount):
    return amount * TAX_RATE
```

#### Level 2 - Extended Context (include if space permits):

```
# Parent class/module structure
class ShoppingCart(BaseCart):
    # gives context about inheritance
    
# Related test files
def test_calculatePrice_with_discount():
    # shows expected behavior
    
# Similar patterns in codebase (via RAG)
# Other pricing functions for consistency
```

**Level 3 - Peripheral Context (metadata only):**
```
- File imports: tax_calculator, discount_engine
- Constants used: TAX_RATE, MAX_DISCOUNT
- Called by: 15 other functions (list them)
- Test coverage: 85%
```

#### Step 4: Incremental Tree Updates
Challenge: Rebuilding entire tree on every PR is slow.
Solution: Incremental updates

```
class SemanticTree:
    def update_from_diff(self, diff):
        for changed_file in diff.files:
            # 1. Re-parse only changed files
            new_ast = parse_file(changed_file)
            
            # 2. Diff the AST (what functions/classes changed)
            changes = diff_ast(old_ast, new_ast)
            
            # 3. Update affected nodes in graph
            for change in changes:
                if change.type == "function_modified":
                    # Update function node
                    update_node(change.function_name)
                    
                    # Update edges (calls, called_by)
                    recompute_dependencies(change.function_name)
                    
                elif change.type == "function_added":
                    # Add new node
                    # Connect to callers/callees
                    
                elif change.type == "function_deleted":
                    # Remove node
                    # Find orphaned callers (breaking change!)
```

#### Step 5: Context Window Management
Problem: LLMs have token limits. We can't send entire codebase.
Solution: Smart context selection

```
def build_review_context(changed_function, max_tokens=8000):
    context = []
    tokens_used = 0
    
    # Priority 1: The changed code itself (always include)
    context.append(changed_function.code)
    tokens_used += count_tokens(changed_function.code)
    
    # Priority 2: Direct callers (breaking change risk)
    for caller in changed_function.called_by:
        if tokens_used < max_tokens * 0.4:
            context.append(caller.code)
            tokens_used += count_tokens(caller.code)
    
    # Priority 3: Direct callees (understanding dependencies)
    for callee in changed_function.calls:
        if tokens_used < max_tokens * 0.6:
            context.append(callee.code)
            tokens_used += count_tokens(callee.code)
    
    # Priority 4: Tests (expected behavior)
    for test in changed_function.tests:
        if tokens_used < max_tokens * 0.8:
            context.append(test.code)
            tokens_used += count_tokens(test.code)
    
    # Priority 5: RAG similar code (best practices)
    if tokens_used < max_tokens * 0.9:
        similar = vector_search(changed_function.embedding)
        context.append(similar)
    
    return context
```


