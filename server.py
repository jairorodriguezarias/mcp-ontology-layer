import sys
import json
from owlready2 import *

ONTOLOGY_PATH = "core.owl"

def handle_list_classes():
    try:
        onto = get_ontology(f"file://{ONTOLOGY_PATH}").load()
        classes = [cls.name for cls in list(onto.classes())]
        return f"Clases en la ontologia: {classes}"
    except Exception as e:
        return f"Error leyendo ontologia: {e}"

def handle_add_subclass(new_class, parent_class):
    try:
        onto = get_ontology(f"file://{ONTOLOGY_PATH}").load()
        Parent = IRIS[f"{onto.base_iri}{parent_class}"]
        if not Parent:
            return f"Error: La clase padre {parent_class} no existe."
        with onto:
            types.new_class(new_class, (Parent,))
        onto.save(file=ONTOLOGY_PATH, format="rdfxml")
        return f"Exito: {new_class} anadida como subclase de {parent_class}"
    except Exception as e:
        return f"Error inyectando clase: {e}"

def main():
    tools = [
        {
            "name": "list_classes",
            "description": "Lista todas las clases actuales en la ontologia bancaria.",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "add_subclass",
            "description": "Anade una nueva subclase a la ontologia.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "new_class": {"type": "string", "description": "Nombre de la nueva clase"},
                    "parent_class": {"type": "string", "description": "Nombre de la clase padre"}
                },
                "required": ["new_class", "parent_class"]
            }
        }
    ]

    for line in sys.stdin:
        if not line.strip():
            continue
        req = json.loads(line)
        method = req.get("method")
        msg_id = req.get("id")

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "Banco_Ontology_Manager", "version": "1.0"}
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
            else:
                text = "Herramienta no reconocida."

            res = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": text}]}
            }
        else:
            res = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Metodo no encontrado"}}

        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
