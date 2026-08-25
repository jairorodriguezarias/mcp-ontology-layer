import os
import rdflib
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL, Namespace
from pyvis.network import Network

CORE = Namespace("http://banco.es/ontologies/core#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")

# Layer-specific visual encoding
STYLE_MAP = {
    "TBOX_CLASS": {"color": "#3498DB", "shape": "box", "size": 25},            # Blue
    "ABOX_LOAN": {"color": "#2ECC71", "shape": "dot", "size": 22},             # Green (Layer 1)
    "LAYER2_DISJOINT": {"color": "#E67E22", "shape": "hexagon", "size": 20},    # Orange (Layer 2)
    "LAYER3_HIGHRISK": {"color": "#E74C3C", "shape": "diamond", "size": 28},    # Red (Layer 3 Inferred)
    "LAYER4_SKOS": {"color": "#F1C40F", "shape": "triangle", "size": 22},       # Yellow (Layer 4)
    "LAYER5_PROV": {"color": "#9B59B6", "shape": "square", "size": 24},         # Purple (Layer 5)
    "LITERAL": {"color": "#95A5A6", "shape": "ellipse", "size": 15},            # Gray
}

def shorten_uri(uri_str: str) -> str:
    """Shorten common namespaces for readable labels."""
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
    """Classify an RDF term into one of the 5 neuro-symbolic layers."""
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
    if CORE.PersonalLoan in types or CORE.FinancialProduct in types:
        return "ABOX_LOAN"
    
    return "ABOX_LOAN"


def build_interactive_graph(owl_path="core.owl", output_html="graph.html"):
    if not os.path.exists(owl_path):
        raise FileNotFoundError(f"Missing ontology file: {owl_path}")

    g = Graph()
    g.parse(owl_path, format="xml")

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
        tooltip = f"Type: {category}\nURI/Val: {term_id}"

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

    # Filtered edge emission
    for s, p, o in g:
        # Ignore raw Ontology header declarations
        if o == OWL.Ontology:
            continue

        s_id = register_node(s)
        o_id = register_node(o)
        p_label = shorten_uri(str(p))

        # Edge styling by predicate type
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

    net.save_graph(output_html)
    print(f"✔ Knowledge graph successfully exported to: {os.path.abspath(output_html)}")


if __name__ == "__main__":
    build_interactive_graph()