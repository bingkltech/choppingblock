"""
🕸️ primitive_graph.py — Semantic Knowledge Graph Tool
Builds a lightweight Knowledge Graph (AST-based) of the workspace so agents 
can query relationships, find function definitions, and navigate code natively.
"""

import os
import ast
import json
import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

GRAPH_FILE = ".graph_index.json"

class GraphifyIndexer:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.graph_path = os.path.join(workspace_path, GRAPH_FILE)
        self.graph = {
            "files": {},
            "symbols": {}, # symbol_name -> list of {file, type, line}
        }

    def build(self) -> dict:
        """Walk the workspace and build the semantic graph."""
        logger.info("🕸️ Graphify: Scanning workspace %s", self.workspace_path)
        self.graph = {"files": {}, "symbols": {}}

        if not os.path.exists(self.workspace_path):
            return self.graph

        for root, dirs, files in os.walk(self.workspace_path):
            # Skip hidden dirs and node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != "node_modules" and d != "__pycache__"]

            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.workspace_path)

                if file.endswith('.py'):
                    self._parse_python(filepath, rel_path)
                elif file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    self._parse_javascript(filepath, rel_path)

        # Save to disk
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(self.graph, f, indent=2)

        logger.info("🕸️ Graphify: Built graph with %d files indexed.", len(self.graph["files"]))
        return self.graph

    def _add_symbol(self, name: str, sym_type: str, rel_path: str, line: int):
        if name not in self.graph["symbols"]:
            self.graph["symbols"][name] = []
        
        node = {"type": sym_type, "file": rel_path, "line": line}
        if node not in self.graph["symbols"][name]:
            self.graph["symbols"][name].append(node)

        if rel_path not in self.graph["files"]:
            self.graph["files"][rel_path] = []
        self.graph["files"][rel_path].append({"name": name, "type": sym_type, "line": line})

    def _parse_python(self, filepath: str, rel_path: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self._add_symbol(node.name, "Function", rel_path, node.lineno)
                elif isinstance(node, ast.AsyncFunctionDef):
                    self._add_symbol(node.name, "AsyncFunction", rel_path, node.lineno)
                elif isinstance(node, ast.ClassDef):
                    self._add_symbol(node.name, "Class", rel_path, node.lineno)
        except Exception as e:
            logger.debug("🕸️ Graphify: Failed to parse Python file %s: %s", rel_path, e)

    def _parse_javascript(self, filepath: str, rel_path: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Very basic regex for JS/TS classes and functions
            class_matches = re.finditer(r'class\s+([A-Za-z0-9_]+)', content)
            func_matches = re.finditer(r'(function\s+([A-Za-z0-9_]+))|(const\s+([A-Za-z0-9_]+)\s*=\s*(async\s+)?(\([^)]*\)|[a-zA-Z0-9_]+)\s*=>)', content)

            for match in class_matches:
                self._add_symbol(match.group(1), "Class", rel_path, content[:match.start()].count('\n') + 1)
            
            for match in func_matches:
                name = match.group(2) or match.group(4)
                if name:
                    self._add_symbol(name, "Function", rel_path, content[:match.start()].count('\n') + 1)
        except Exception as e:
            logger.debug("🕸️ Graphify: Failed to parse JS/TS file %s: %s", rel_path, e)


def build_knowledge_graph(workspace_path: str) -> dict:
    """Entry point to build the graph."""
    indexer = GraphifyIndexer(workspace_path)
    return indexer.build()


def query_graph(workspace_path: str, query: str) -> dict:
    """
    Search the graph for a specific keyword/symbol.
    Returns files and line numbers where the symbol is defined.
    """
    graph_path = os.path.join(workspace_path, GRAPH_FILE)
    if not os.path.exists(graph_path):
        build_knowledge_graph(workspace_path)
        
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            graph = json.load(f)
            
        exact_matches = graph["symbols"].get(query, [])
        
        # Fuzzy match
        fuzzy_matches = {}
        for sym_name, nodes in graph["symbols"].items():
            if query.lower() in sym_name.lower() and sym_name != query:
                fuzzy_matches[sym_name] = nodes
                
        return {
            "success": True,
            "query": query,
            "exact_matches": exact_matches,
            "related_matches": fuzzy_matches
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_file_outline(workspace_path: str, filepath: str) -> dict:
    """Returns all symbols defined in a specific file."""
    graph_path = os.path.join(workspace_path, GRAPH_FILE)
    if not os.path.exists(graph_path):
        build_knowledge_graph(workspace_path)
        
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            graph = json.load(f)
            
        symbols = graph["files"].get(filepath, [])
        return {
            "success": True,
            "file": filepath,
            "symbols": symbols
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
