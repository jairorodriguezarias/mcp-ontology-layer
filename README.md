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

---

## 🛡️ The 5 Neuro-Symbolic Layers

| Layer | Standard / Engine | Responsibility | Rejection Mode / Behavior |
| :--- | :--- | :--- | :--- |
| **1. Validation** | **W3C SHACL Core** (`pyshacl`) | Enforces schema constraints, datatypes (`xsd:decimal`), term boundaries ($6 \le \text{term} \le 120$), and currency enums (`EUR`, `USD`, `GBP`). | Pre-execution rejection (`SHACLShapeViolation`). |
| **2. Reasoning** | **OWL 2 DL HermiT** (`CommandLine -c`) | Mathematical DL consistency check. Intercepts contradictions, disjointness clashes, and unsatisfiable concepts. | Transaction rollback (`LogicalInconsistency`). |
| **3. Calculation** | **SHACL-AF** (`sh:SPARQLRule`) | Runs deterministic construct rules to materialize derived facts in-memory (e.g., auto-classifying high-risk exposure). | In-place triple materialization (`inplace=True`). |
| **4. Terminology** | **W3C SKOS** (`skos:Concept`) | Standardizes banking taxonomy concepts and enforces required multilingual labels (`@es`, `@en`). | Terminology rejection (`SKOSTerminologyError`). |
| **5. Provenance** | **W3C PROV-O** (`prov:Agent`) | Automatically binds entity lineage, agent identity, and ISO UTC timestamps to committed individuals. | Auto-injected prior to disk persistence. |

---

## 📂 Repository Structure

* **`core.owl`**: Persistent banking knowledge graph serialized in W3C OWL 2 RDF/XML.
* **`shapes.ttl`**: W3C SHACL validation shapes and SHACL-AF SPARQL construct rules.
* **`server.py`**: Native JSON-RPC 2.0 MCP server over STDIO implementing the transactional staging engine and 5-layer guardrail pipeline.
* **`test_suite.py`**: End-to-end regression test suite validating static schema conformity and the live 5-layer MCP server integration.
* **`agente.py`**: Batch agent executing end-to-end ontology goals via Ollama.
* **`agent_interactive.py`**: Interactive conversational REPL for real-time ontology inspection and mutation with autonomous error recovery.
* **`requirements.txt`**: Project dependencies (`owlready2`, `rdflib`, `pyshacl`, `pyvis`).
* **`graph.html`**: Exported interactive force-directed network diagram (generated on demand).

---

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

8. Create specific example

```bash
python3 interative_agent.py

You > Create a 'PersonalLoan' under 'Loan', instantiate 'Loan_Auto_2026_01', set principal to 24500.00 EUR at 5.75% for 60 months, and verify via SPARQL. 

You > Attach properties to Loan_Auto_2026_01: principal 24500.00 EUR, rate 5.75%, term 60 months. Then list all personal loans with 60 months.

  ⚙️ [MCP Tool Call] list_classes({})
  📥 [MCP Output] Ontology classes: ['FinancialProduct', 'Loan', 'PrestamoHipotecario', 'PersonalLoan']

  ⚙️ [MCP Tool Call] execute_sparql({
      "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o . FILTER(CONTAINS(STR(?s), 'Loan_Auto_2026_01')) } LIMIT 50"
    })
  📥 [MCP Output] [
    ["[http://banco.es/ontologies/core#Loan_Auto_2026_01](http://banco.es/ontologies/core#Loan_Auto_2026_01)", "[http://www.w3.org/1999/02/22-rdf-syntax-ns#type](http://www.w3.org/1999/02/22-rdf-syntax-ns#type)", "[http://www.w3.org/2002/07/owl#NamedIndividual](http://www.w3.org/2002/07/owl#NamedIndividual)"],
    ["[http://banco.es/ontologies/core#Loan_Auto_2026_01](http://banco.es/ontologies/core#Loan_Auto_2026_01)", "[http://www.w3.org/1999/02/22-rdf-syntax-ns#type](http://www.w3.org/1999/02/22-rdf-syntax-ns#type)", "[http://banco.es/ontologies/core#PersonalLoan](http://banco.es/ontologies/core#PersonalLoan)"]
  ]

  ⚙️ [MCP Tool Call] execute_sparql({
      "query": "PREFIX core: [http://banco.es/ontologies/core#](http://banco.es/ontologies/core#)\nPREFIX xsd:  [http://www.w3.org/2001/XMLSchema#](http://www.w3.org/2001/XMLSchema#)\n\nINSERT DATA {\n  core:Loan_Auto_2026_01 core:principal  \"24500.00\"^^xsd:decimal ;\n                         core:currency   \"EUR\" ;\n                         core:rate       \"5.75\"^^xsd:decimal ;\n                         core:term       \"60\"^^xsd:integer .\n}"
    })
  📥 [MCP Output] SPARQL Update executed successfully and changes persisted to core.owl.

  ⚙️ [MCP Tool Call] execute_sparql({
      "query": "PREFIX core: [http://banco.es/ontologies/core#](http://banco.es/ontologies/core#)\n\nSELECT ?loan ?principal ?currency ?rate ?term WHERE {\n  ?loan a core:PersonalLoan ;\n        core:term ?term ;\n        core:principal ?principal ;\n        core:currency ?currency ;\n        core:rate ?rate .\n  FILTER(?term = 60)\n}"
    })
  📥 [MCP Output] [
    ["[http://banco.es/ontologies/core#Loan_Auto_2026_01](http://banco.es/ontologies/core#Loan_Auto_2026_01)", "24500.00", "EUR", "5.75", "60"]
  ]

Agent > Summary of operations:
- Attached properties to 'Loan_Auto_2026_01' (Principal: 24,500.00 EUR, Rate: 5.75%, Term: 60 months).
- Verified graph persistence in core.owl.
- Filtered personal loans matching a 60-month term: 1 result found (Loan_Auto_2026_01).

you >  Export the current graph visualization.


9. Layer 1 (SHACL Violation)

you > Create a PersonalLoan named 'Loan_BadTerm_01' with principal 15000.00 EUR at 6.00% for 240 months.

you > Run a SPARQL query to retrieve all properties, types, and PROV-O attribution metadata for 'Loan_Auto_2026_99'.

10. Layer 2 (HermiT Violation)

you > First, add a new class 'DepositAccount' under 'FinancialProduct'. Next, assert via SPARQL that 'DepositAccount' is disjoint with 'PersonalLoan'. Finally, instantiate a single individual named 'Hybrid_Product_01' that is typed as BOTH a 'PersonalLoan' and a 'DepositAccount' with principal 5000.00 EUR, rate 3.50%, and term 24 months.


11. Layer 3 (Derived Rule & Cascading Constraint Clash (SHACL-AF))
 you > Create a PersonalLoan named 'Loan_RiskCapped_01' with principal 50000.00 EUR, an interest rate of 16.50%, and a term of 84 months.

12. Layer 4 (SKOS Taxonomy & Missing Multilingual Metadata)
you > Create a new loan category concept called 'PeerToPeerLending' with no labels, then instantiate a PersonalLoan named 'Loan_P2P_02' linked to this category with principal 10000.00 EUR, rate 4.50%, and term 24 months.

13. Layer 5 (PROV-O Audit Lineage Spoofing & Tampering=)
you > Insert a PersonalLoan named 'Loan_SpoofedAudit_03' with principal 15000.00 EUR, rate 5.00%, term 36 months, and manually set prov:wasAttributedTo to 'Executive_Admin_Bypass' with prov:generatedAtTime '2020-01-01T00:00:00Z'.

## KG

# 1. Export graph
python3 visualize_graph.py

# 2. View in browser
open graph.html


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