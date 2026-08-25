import sys
import json
from owlready2 import get_ontology, IRIS, types, sync_reasoner_hermit, default_world
from pyvis.network import Network
import rdflib

ONTOLOGY_PATH = "core.owl"

def handle_list_classes():
    try:
        onto = get_ontology(f"file://{ONTOLOGY_PATH}").load()
        classes = [cls.name for cls in list(onto.classes())]
        return f"Ontology classes: {classes}"
    except Exception as e:
        return f"Error reading ontology: {e}"

def handle_add_subclass(new_class: str, parent_class: str):
    try:
        onto = get_ontology(f"file://{ONTOLOGY_PATH}").load()
        Parent = IRIS[f"{onto.base_iri}{parent_class}"]
        if not Parent:
            return f"Error: Parent class '{parent_class}' does not exist."
        
        with onto:
            types.new_class(new_class, (Parent,))
        
        onto.save(file=ONTOLOGY_PATH, format="rdfxml")
        return f"Success: '{new_class}' created as subclass of '{parent_class}'."
    except Exception as e:
        return f"Error adding subclass: {e}"

def handle_create_individual(class_name: str, individual_id: str):
    try:
        onto = get_ontology(f"file://{ONTOLOGY_PATH}").load()
        Cls = IRIS[f"{onto.base_iri}{class_name}"]
        if not Cls:
            return f"Error: Class '{class_name}' does not exist."
        
        with onto:
            Cls(individual_id)
        
        onto.save(file=ONTOLOGY_PATH, format="rdfxml")
        return f"Success: Created individual '{individual_id}' of type '{class_name}'."
    except Exception as e:
        return f"Error creating individual: {e}"

def handle_check_consistency():
    try:
        onto = get_ontology(f"file://{ONTOLOGY_PATH}").load()
        with onto:
            sync_reasoner_hermit(infer_property_values=True)
        return "Consistency Check (HermiT): The ontology is logically consistent. No unsatisfiable classes found."
    except Exception as e:
        return f"Consistency Check (HermiT) Failed: Inconsistency detected -> {e}"

def handle_execute_sparql(query: str):
    try:
        get_ontology(f"file://{ONTOLOGY_PATH}").load()
        graph = default_world.as_rdflib_graph()
        results = graph.query(query)
        formatted_results = [list(map(str, row)) for row in results]
        return json.dumps(formatted_results, indent=2)
    except Exception as e:
        return f"SPARQL execution error: {e}"

def handle_export_graph(output_html: str = "graph.html"):
    try:
        g = rdflib.Graph()
        g.parse(ONTOLOGY_PATH, format="xml")
        
        net = Network(height="750px", width="100%", directed=True, bgcolor="#1a1a1a", font_color="white")
        for s, p, o in g:
            s_label = str(s).split("#")[-1].split("/")[-1]
            o_label = str(o).split("#")[-1].split("/")[-1]
            p_label = str(p).split("#")[-1].split("/")[-1]
            
            if s_label and o_label:
                net.add_node(str(s), label=s_label, color="#4CAF50")
                net.add_node(str(o), label=o_label, color="#2196F3")
                net.add_edge(str(s), str(o), title=p_label, label=p_label)
                
        net.save_graph(output_html)
        return f"Success: Interactive graph exported to '{output_html}'."
    except Exception as e:
        return f"Error exporting graph: {e}"

def main():
    tools = [
        {
            "name": "list_classes",
            "description": "Lists all classes currently present in the banking ontology.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "add_subclass",
            "description": "Adds a new subclass to an existing parent class in the ontology.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "new_class": {"type": "string", "description": "Name of the new entity class"},
                    "parent_class": {"type": "string", "description": "Name of the existing parent class"}
                },
                "required": ["new_class", "parent_class"]
            }
        },
        {
            "name": "create_individual",
            "description": "Instantiates a concrete individual (ABox entity) belonging to a specific class.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "class_name": {"type": "string", "description": "Class type for the individual"},
                    "individual_id": {"type": "string", "description": "Unique identifier for the individual"}
                },
                "required": ["class_name", "individual_id"]
            }
        },
        {
            "name": "check_consistency",
            "description": "Runs the HermiT Description Logic (DL) reasoner to verify logical consistency and compute inferences.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "execute_sparql",
            "description": "Executes a SPARQL query against the RDF knowledge graph.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Standard W3C SPARQL query string"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "export_graph",
            "description": "Generates an interactive HTML visual representation of the RDF knowledge graph using PyVis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "output_html": {"type": "string", "description": "Output HTML filename (e.g., 'graph.html')"}
                }
            }
        }
    ]

    for line in sys.stdin:
        if not line.strip():
            continue
        
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method")
        msg_id = req.get("id")

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "Banco_Ontology_Manager", "version": "1.3.0"}
                }
            }
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            res = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})

            if name == "list_classes":
                text = handle_list_classes()
            elif name == "add_subclass":
                text = handle_add_subclass(args.get("new_class"), args.get("parent_class"))
            elif name == "create_individual":
                text = handle_create_individual(args.get("class_name"), args.get("individual_id"))
            elif name == "check_consistency":
                text = handle_check_consistency()
            elif name == "execute_sparql":
                text = handle_execute_sparql(args.get("query"))
            elif name == "export_graph":
                text = handle_export_graph(args.get("output_html", "graph.html"))
            else:
                text = f"Tool '{name}' is not recognized."

            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": text}]}
            }
        else:
            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": "Method not found"}
            }

        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()