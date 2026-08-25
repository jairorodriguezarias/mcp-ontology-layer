import sys
import json
import os
import tempfile
import subprocess
from datetime import datetime, timezone
import rdflib
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL, XSD, Namespace
import pyshacl
import owlready2
import owlready2.hermit
from pyvis.network import Network

ONTOLOGY_PATH = os.path.abspath("core.owl")
SHAPES_PATH = os.path.abspath("shapes.ttl")

CORE = Namespace("http://banco.es/ontologies/core#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")

# Resolve HermiT Java paths
JAVA_EXE = getattr(owlready2, "JAVA_EXE", "java")
HERMIT_CLASSPATH = getattr(owlready2.hermit, "HERMIT_CLASSPATH", None)
if not HERMIT_CLASSPATH:
    hermit_dir = os.path.join(os.path.dirname(owlready2.__file__), "hermit")
    sep = ";" if sys.platform.startswith("win") else ":"
    HERMIT_CLASSPATH = f"{hermit_dir}{sep}{os.path.join(hermit_dir, 'HermiT.jar')}"

# Ensure base ontology exists
if not os.path.exists(ONTOLOGY_PATH):
    init_g = Graph()
    init_g.bind("core", CORE)
    init_g.bind("owl", OWL)
    init_g.bind("skos", SKOS)
    init_g.bind("prov", PROV)
    init_g.add((URIRef("http://banco.es/ontologies/core"), RDF.type, OWL.Ontology))
    init_g.add((CORE.FinancialProduct, RDF.type, OWL.Class))
    init_g.add((CORE.PersonalLoan, RDF.type, OWL.Class))
    init_g.add((CORE.HighRiskProduct, RDF.type, OWL.Class))
    init_g.add((CORE.PersonalLoan, RDFS.subClassOf, CORE.FinancialProduct))
    init_g.add((CORE.HighRiskProduct, RDFS.subClassOf, CORE.FinancialProduct))
    init_g.serialize(destination=ONTOLOGY_PATH, format="xml")


# --- 5-Layer Visual Graph Engine ---

STYLE_MAP = {
    "TBOX_CLASS": {"color": "#3498DB", "shape": "box", "size": 25},            # Blue
    "ABOX_LOAN": {"color": "#2ECC71", "shape": "dot", "size": 22},             # Green (L1)
    "LAYER3_HIGHRISK": {"color": "#E74C3C", "shape": "diamond", "size": 28},    # Red (L3)
    "LAYER4_SKOS": {"color": "#F1C40F", "shape": "triangle", "size": 22},       # Yellow (L4)
    "LAYER5_PROV": {"color": "#9B59B6", "shape": "square", "size": 24},         # Purple (L5)
    "LITERAL": {"color": "#95A5A6", "shape": "ellipse", "size": 15},            # Gray
}

def shorten_uri(uri_str: str) -> str:
    for prefix, base in [
        ("core:", "http://banco.es/ontologies/core#"),
        ("skos:", "http://www.w3.org/2004/02/skos/core#"),
        ("prov:", "http://www.w3.org/ns/prov#"),
        ("owl:", "http://www.w3.org/2002/07/owl#"),
        ("rdfs:", "http://www.w3.org/2000/01/rdf-schema#"),
        ("rdf:", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ]:
        if uri_str.startswith(base):
            return uri_str.replace(base, prefix)
    return uri_str.split("#")[-1].split("/")[-1]

def get_node_category(node, graph: Graph) -> str:
    if isinstance(node, Literal):
        return "LITERAL"
    types = set(graph.objects(node, RDF.type))
    if OWL.Class in types or (node, RDF.type, OWL.Class) in graph:
        return "TBOX_CLASS"
    if SKOS.Concept in types:
        return "LAYER4_SKOS"
    if PROV.Agent in types or "Agent" in str(node):
        return "LAYER5_PROV"
    if CORE.HighRiskProduct in types:
        return "LAYER3_HIGHRISK"
    return "ABOX_LOAN"

def generate_interactive_graph(output_filename="graph.html") -> dict:
    if not os.path.exists(ONTOLOGY_PATH):
        return {"status": "ERROR", "message": f"Ontology file {ONTOLOGY_PATH} does not exist."}

    g = Graph()
    g.parse(ONTOLOGY_PATH, format="xml")

    net = Network(height="850px", width="100%", bgcolor="#1e1e24", font_color="#f5f6fa", directed=True)
    net.force_atlas_2based(gravity=-60, central_gravity=0.015, spring_length=110, spring_strength=0.08, damping=0.5)

    added_nodes = set()

    def register_node(term):
        term_id = str(term)
        if term_id in added_nodes:
            return term_id

        category = get_node_category(term, g)
        style = STYLE_MAP[category]
        label = str(term) if isinstance(term, Literal) else shorten_uri(term_id)
        tooltip = f"Category: {category}\nURI: {term_id}"

        net.add_node(
            term_id,
            label=label,
            title=tooltip,
            color=style["color"],
            shape=style["shape"],
            size=style["size"],
            font={"size": 14, "color": "#ffffff"}
        )
        added_nodes.add(term_id)
        return term_id

    for s, p, o in g:
        if o == OWL.Ontology:
            continue
        s_id = register_node(s)
        o_id = register_node(o)
        p_label = shorten_uri(str(p))

        edge_color = "#7f8c8d"
        dashes = False
        if p == RDF.type:
            edge_color = "#3498DB"
            dashes = True
        elif p == RDFS.subClassOf:
            edge_color = "#2980B9"
        elif "prov" in str(p):
            edge_color = "#9B59B6"
        elif "loanCategory" in str(p) or "skos" in str(p):
            edge_color = "#F1C40F"

        net.add_edge(s_id, o_id, label=p_label, color=edge_color, dashes=dashes, arrows="to")

    abs_output = os.path.abspath(output_filename)
    net.save_graph(abs_output)

    return {
        "status": "SUCCESS",
        "output_file": abs_output,
        "nodes_rendered": len(added_nodes),
        "triples_visualized": len(g),
        "message": f"Interactive 5-layer graph visualization saved to {abs_output}"
    }


# --- 5-Layer Transactional Runtime ---

class FullNeuroSymbolicRuntime:
    @staticmethod
    def transactional_update(sparql_update: str, agent_id: str = "MCP_Autonomous_Agent") -> dict:
        staging_graph = Graph()
        staging_graph.bind("core", CORE)
        staging_graph.bind("skos", SKOS)
        staging_graph.bind("prov", PROV)

        try:
            staging_graph.parse(ONTOLOGY_PATH, format="xml")
        except Exception as e:
            return {"status": "REJECTED", "error_type": "StorageError", "details": f"Failed to load core.owl: {e}"}

        try:
            staging_graph.update(sparql_update)
        except Exception as e:
            return {"status": "REJECTED", "error_type": "SPARQLSyntaxError", "details": str(e)}

        # LAYER 1 & 3: SHACL Validation & Rule Inferences
        inferred_rules_count = 0
        if os.path.exists(SHAPES_PATH):
            try:
                shapes_graph = Graph().parse(SHAPES_PATH, format="turtle")
                initial_count = len(staging_graph)

                conforms, _, report_text = pyshacl.validate(
                    data_graph=staging_graph,
                    shacl_graph=shapes_graph,
                    advanced=True,
                    inplace=True,
                    iterate_rules=True,
                    inference="rdfs",
                    abort_on_first=False
                )
                if not conforms:
                    return {
                        "status": "REJECTED",
                        "error_type": "SHACLShapeViolation",
                        "details": report_text.strip()
                    }
                inferred_rules_count = len(staging_graph) - initial_count
            except Exception as e:
                return {"status": "REJECTED", "error_type": "SHACLExecutionError", "details": str(e)}

        # LAYER 2: HermiT DL Consistency Check
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
            return {"status": "REJECTED", "error_type": "HermiTExecutionError", "details": str(e)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        # LAYER 4: SKOS Terminology Check
        for _, _, concept_uri in staging_graph.triples((None, CORE.loanCategory, None)):
            labels = list(staging_graph.objects(concept_uri, SKOS.prefLabel))
            if not labels:
                return {
                    "status": "REJECTED",
                    "error_type": "SKOSTerminologyError",
                    "details": f"Concept {concept_uri} is missing required skos:prefLabel definitions."
                }

        # LAYER 5: PROV-O Audit Stamping
        now_iso = datetime.now(timezone.utc).isoformat()
        agent_uri = CORE[agent_id]
        staging_graph.add((agent_uri, RDF.type, PROV.Agent))

        for s, _, _ in staging_graph.triples((None, RDF.type, CORE.PersonalLoan)):
            staging_graph.add((s, PROV.wasAttributedTo, agent_uri))
            staging_graph.add((s, PROV.generatedAtTime, Literal(now_iso, datatype=XSD.dateTime)))

        # Commit to persistence
        staging_graph.serialize(destination=ONTOLOGY_PATH, format="xml")
        return {
            "status": "SUCCESS",
            "message": "Mutation verified across all 5 runtime layers and committed.",
            "pipeline_metrics": {
                "layer_1_shacl": "PASSED",
                "layer_2_hermit": "PASSED",
                "layer_3_rules_inferred_triples": inferred_rules_count,
                "layer_4_skos_validated": True,
                "layer_5_prov_stamped": True
            }
        }


# --- Tool Dispatcher ---

def dispatch_tool(tool_name: str, args: dict) -> dict:
    if tool_name == "execute_sparql":
        query = args.get("query", "")
        is_update = any(k in query.upper() for k in ["INSERT", "DELETE", "CLEAR", "CREATE", "DROP", "LOAD"])
        if is_update:
            return FullNeuroSymbolicRuntime.transactional_update(query)
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
        return FullNeuroSymbolicRuntime.transactional_update(sparql_subclass)

    elif tool_name == "export_graph":
        output_file = args.get("output_file", "graph.html")
        return generate_interactive_graph(output_file)

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
                    "serverInfo": {"name": "NeuroSymbolicOntologyServer", "version": "1.1.0"}
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
                            "description": "Execute a SPARQL Query or UPDATE through the 5-layer neuro-symbolic guardrail.",
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
                        },
                        {
                            "name": "export_graph",
                            "description": "Export an interactive force-directed PyVis HTML graph with color-coded nodes for each of the 5 neuro-symbolic layers.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "output_file": {
                                        "type": "string",
                                        "description": "Target HTML file name (default: graph.html)"
                                    }
                                }
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
    sys.stderr.write("Neuro-Symbolic Server started. Listening on stdio...\n")
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