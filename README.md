# Local MCP Semantic Agent with OWL, HermiT & Ollama

A fully local execution architecture on macOS for deterministic inspection, mutation, Description Logic (DL) reasoning, and SPARQL querying of banking ontologies (OWL/RDF) using LLM agents and the Model Context Protocol (MCP) over STDIO.

## Core Capabilities

* **HermiT DL Reasoning:** Integrated Description Logic reasoner (`sync_reasoner_hermit`) to verify ontology consistency, compute inferred class hierarchies, and detect unsatisfiable classes.
* **SPARQL Query Engine:** Direct W3C SPARQL query execution over the RDF knowledge graph via RDFLib, allowing complex semantic queries, filtering, and aggregations.
* **Taxonomy & Instance Mutation (TBox/ABox):** Dynamic insertion of OWL classes, subclass hierarchies, and named individual assertions.
* **Interactive Force-Directed Visualizations:** Automatic export of the knowledge graph into interactive PyVis HTML networks.
* **Dual Execution Modes:** Automated batch pipeline (`agente.py`) and persistent conversational REPL (`agent_interactive.py`).

## Architecture

The system decouples model reasoning from graph execution across four core layers:

1. **Agent Orchestrator:**
   * **`agente.py`**: Automated pipeline executing batch agent goals end-to-end.
   * **`agent_interactive.py`**: Multi-turn conversational REPL maintaining state and executing dynamic multi-step semantic workflows.
2. **LLM Engine (`Ollama`):** Executes local models (e.g., `glm-5.2:cloud`, `qwen2.5-coder`) to perform intent decomposition and parameter formatting without direct file access.
3. **MCP Server (`server.py`):** JSON-RPC 2.0 interface communicating over STDIO, translating model tool calls into deterministic semantic graph operations via Owlready2 and RDFLib.
4. **Semantic Layer (`core.owl`):** Persistent W3C RDF/XML ontology graph verified with the HermiT DL reasoner.

## Repository Structure

* **`core.owl`**: Base banking ontology file in RDF/XML format (W3C OWL Standard).
* **`server.py`**: Native JSON-RPC 2.0 MCP server providing TBox/ABox mutation, SPARQL execution, HermiT reasoning, and PyVis graph exports.
* **`agente.py`**: Automated batch execution agent connecting Ollama to the MCP server.
* **`agent_interactive.py`**: Interactive conversational REPL agent for real-time ontology management.
* **`requirements.txt`**: Python dependencies (`owlready2`, `rdflib`, `pyvis`).
* **`graph.html`**: Exported interactive HTML graph visualization (generated on demand).
* **`README.md`**: Project architecture, tool documentation, and setup instructions.

## Prerequisites

* **OS:** macOS (Apple Silicon or Intel)
* **Python:** 3.10 or higher
* **Ollama:** Installed and running locally
* **Java:** OpenJDK / JRE (required by Owlready2 for the HermiT reasoner)

## Installation & Environment Setup

1. Clone the repository and navigate to the project directory:
```bash
git clone [https://github.com/jairorodriguezarias/mcp-ontology-layer.git](https://github.com/jairorodriguezarias/mcp-ontology-layer.git)
cd mcp-ontology-layer
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

4 . Download the model in Ollama:
```bash
ollama pull glm-5.2:cloud
```

5. Run the agent demo:
```bash
python3 agente.py
```

6 . 
```bash
python3 agent_interactive.py
```

7. Visualizing the Knowledge Graph
```bash
open graph.html
```

Available MCP Tools
* **list_classes**
* **Parameters:** None
* **Description:** Loads `core.owl` and returns all registered ontology classes.


* **add_subclass**
* **Parameters:** `new_class` (string, required), `parent_class` (string, required)
* **Description:** Inserts a new class under an existing parent class and saves the updated RDF/XML graph to disk.


* **create_individual**
* **Parameters:** `class_name` (string, required), `individual_id` (string, required)
* **Description:** Instantiates a concrete ABox individual belonging to a specific class.


* **check_consistency**
* **Parameters:** None
* **Description:** Runs the HermiT Description Logic (DL) reasoner to verify logical consistency and detect unsatisfiable classes.


* **execute_sparql**
* **Parameters:** `query` (string, required)
* **Description:** Executes a standard W3C SPARQL query against the RDF knowledge graph.


* **export_graph**
* **Parameters:** `output_html` (string, optional; default: `graph.html`)
* **Description:** Generates an interactive force-directed HTML graph visualization of the ontology using PyVis.