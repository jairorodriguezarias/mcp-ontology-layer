import sys
import json
import os
import tempfile
import subprocess
import rdflib
from rdflib import Graph, URIRef, RDF, RDFS, OWL, Namespace
import pyshacl
import owlready2
import owlready2.hermit

ONTOLOGY_PATH = os.path.abspath("core.owl")
SHAPES_PATH = os.path.abspath("shapes.ttl")
CORE = Namespace("http://banco.es/ontologies/core#")

# Resolve HermiT Java paths
JAVA_EXE = getattr(owlready2, "JAVA_EXE", "java")
HERMIT_CLASSPATH = getattr(owlready2.hermit, "HERMIT_CLASSPATH", None)
if not HERMIT_CLASSPATH:
    hermit_dir = os.path.join(os.path.dirname(owlready2.__file__), "hermit")
    sep = ";" if sys.platform.startswith("win") else ":"
    HERMIT_CLASSPATH = f"{hermit_dir}{sep}{os.path.join(hermit_dir, 'HermiT.jar')}"


class DualValidationGuardrail:
    """Transactional staging engine: RDFLib (SHACL) -> HermiT (OWL 2 DL) -> Disk."""

    @staticmethod
    def transactional_update(sparql_update: str) -> dict:
        # 1. Load current graph into isolated staging graph
        staging_graph = Graph()
        try:
            staging_graph.parse(ONTOLOGY_PATH, format="xml")
        except Exception as e:
            return {"status": "REJECTED", "error_type": "StorageError", "details": f"Failed to load core.owl: {e}"}

        # 2. Apply SPARQL update in staging
        try:
            staging_graph.update(sparql_update)
        except Exception as e:
            return {"status": "REJECTED", "error_type": "SPARQLSyntaxError", "details": str(e)}

        # 3. Stage 1: SHACL Data Quality Validation
        if os.path.exists(SHAPES_PATH):
            try:
                shapes_graph = Graph().parse(SHAPES_PATH, format="turtle")
                conforms, _, report_text = pyshacl.validate(
                    data_graph=staging_graph,
                    shacl_graph=shapes_graph,
                    inference="rdfs",
                    abort_on_first=False
                )
                if not conforms:
                    return {
                        "status": "REJECTED",
                        "error_type": "SHACLShapeViolation",
                        "details": report_text.strip()
                    }
            except Exception as e:
                return {"status": "REJECTED", "error_type": "SHACLExecutionError", "details": str(e)}

        # 4. Stage 2: HermiT DL Consistency Check (-c flag)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                staging_graph.serialize(destination=tmp_path, format="xml")

            cmd = [
                JAVA_EXE,
                "-Xmx2000M",
                "-cp",
                HERMIT_CLASSPATH,
                "org.semanticweb.HermiT.cli.CommandLine",
                "-c",
                f"file://{os.path.abspath(tmp_path)}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            output = (result.stdout + "\n" + result.stderr).strip()

            if result.returncode != 0 or "inconsistent" in output.lower():
                return {
                    "status": "REJECTED",
                    "error_type": "LogicalInconsistency",
                    "details": output
                }

        except Exception as e:
            return {
                "status": "REJECTED",
                "error_type": "HermiTExecutionError",
                "details": str(e)
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        # 5. Atomic Commit: Only write to disk if both SHACL & HermiT passed
        staging_graph.serialize(destination=ONTOLOGY_PATH, format="xml")
        return {
            "status": "SUCCESS",
            "message": "Mutation passed SHACL and HermiT validation and committed."
        }


# --- Tool Dispatcher ---

def dispatch_tool(tool_name: str, args: dict) -> dict:
    if tool_name == "execute_sparql":
        query = args.get("query", "")
        is_update = any(k in query.upper() for k in ["INSERT", "DELETE", "CLEAR", "CREATE", "DROP", "LOAD"])
        
        if is_update:
            return DualValidationGuardrail.transactional_update(query)
        else:
            g = Graph().parse(ONTOLOGY_PATH, format="xml")
            results = g.query(query)
            rows = [[str(term) for term in row] for row in results]
            return {"status": "SUCCESS", "results": rows}

    elif tool_name == "add_subclass":
        new_class = args.get("new_class")
        parent_class = args.get("parent_class", "FinancialProduct")
        sparql_subclass = f"""
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        INSERT DATA {{
            core:{parent_class} a owl:Class .
            core:{new_class} a owl:Class ;
                rdfs:subClassOf core:{parent_class} .
        }}
        """
        return DualValidationGuardrail.transactional_update(sparql_subclass)

    return {"status": "ERROR", "message": f"Unknown tool: {tool_name}"}


# --- MCP Protocol Event Loop ---

def handle_json_rpc(line: str) -> str:
    if not line.strip():
        return ""

    try:
        req = json.loads(line)
        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "OntologyGuardrailServer", "version": "1.0.0"}
                }
            })

        elif method == "notifications/initialized":
            return ""

        elif method == "tools/list":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "execute_sparql",
                            "description": "Execute a SPARQL Query or UPDATE through the validation guardrail.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"query": {"type": "string"}},
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "add_subclass",
                            "description": "Create a new subclass in the ontology.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "new_class": {"type": "string"},
                                    "parent_class": {"type": "string"}
                                },
                                "required": ["new_class", "parent_class"]
                            }
                        }
                    ]
                }
            })

        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            result = dispatch_tool(name, arguments)
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}]
                }
            })

        return json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not supported: {method}"}
        })

    except Exception as e:
        sys.stderr.write(f"Protocol Exception: {e}\n")
        sys.stderr.flush()
        return json.dumps({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": str(e)}
        })


def main():
    sys.stderr.write("Server started. Listening on stdio...\n")
    sys.stderr.flush()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        response = handle_json_rpc(line)
        if response:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()