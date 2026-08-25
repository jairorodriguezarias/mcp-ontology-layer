import subprocess
import json
import os
import sys
import rdflib

DATA_FILE = "core.owl"
SHAPES_FILE = "shapes.ttl"

CORE = rdflib.Namespace("http://banco.es/ontologies/core#")
SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
PROV = rdflib.Namespace("http://www.w3.org/ns/prov#")
RDF = rdflib.RDF
XSD = rdflib.XSD

# =====================================================================
# STAGE 1: Static File & SHACL Schema Validation
# =====================================================================
def run_stage_1_static_tests():
    print("▶ STAGE 1: Static File & SHACL Schema Validation")
    import pyshacl

    for f in [DATA_FILE, SHAPES_FILE]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Missing required file: {f}")

    data_graph = rdflib.Graph().parse(DATA_FILE, format="xml")
    shapes_graph = rdflib.Graph().parse(SHAPES_FILE, format="turtle")

    conforms, _, report_text = pyshacl.validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        inference="rdfs",
        abort_on_first=False
    )

    if not conforms:
        print(f"❌ Static SHACL Validation Failed:\n{report_text}")
        sys.exit(1)

    print("  ✔ Base core.owl satisfies all static shapes.ttl constraints.\n")


# =====================================================================
# STAGE 2: 5-Layer Live MCP Server Integration Suite
# =====================================================================
def run_stage_2_mcp_integration_tests():
    print("▶ STAGE 2: Live MCP Server 5-Layer Integration Suite")

    proc = subprocess.Popen(
        [sys.executable, "-u", "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1
    )

    def send_request(method: str, params: dict = None, req_id: int = 1):
        if proc.poll() is not None:
            raise RuntimeError(f"server.py exited prematurely with code {proc.returncode}")

        payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params:
            payload["params"] = params
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("server.py closed stdout unexpectedly.")
        return json.loads(line)

    def send_notification(method: str, params: dict = None):
        payload = {"jsonrpc": "2.0", "method": method}
        if params:
            payload["params"] = params
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

    def call_tool(name: str, arguments: dict, req_id: int):
        res = send_request("tools/call", {"name": name, "arguments": arguments}, req_id=req_id)
        raw_text = res.get("result", {}).get("content", [{}])[0].get("text", "{}")
        try:
            return json.loads(raw_text)
        except Exception:
            return raw_text

    try:
        # MCP Protocol Handshake
        send_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "TestSuite"}}, req_id=0)
        send_notification("notifications/initialized")

        # -------------------------------------------------------------
        # TEST 2.1: Layer 1 — SHACL Structural Quality Gating
        # -------------------------------------------------------------
        t1_invalid = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:Loan_Bad_L1 a core:PersonalLoan ;
                core:principal "5000.00"^^xsd:decimal ;
                core:currency "DOGE" ;
                core:term 300 ;
                core:rate "5.50"^^xsd:decimal .
        }
        """
        res_l1 = call_tool("execute_sparql", {"query": t1_invalid}, req_id=1)
        assert res_l1.get("status") == "REJECTED" and res_l1.get("error_type") == "SHACLShapeViolation", f"Test 2.1 Failed: {res_l1}"
        print("  ✔ Layer 1 (SHACL): Invalid data (currency/term) rejected before reasoning.")

        # -------------------------------------------------------------
        # TEST 2.2: Layer 2 — HermiT OWL 2 DL Contradiction Gating
        # -------------------------------------------------------------
        call_tool("add_subclass", {"new_class": "DepositAccount", "parent_class": "FinancialProduct"}, req_id=2)
        t2_contradiction = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:PersonalLoan owl:disjointWith core:DepositAccount .
            core:Prod_Clash_L2 a core:PersonalLoan, core:DepositAccount ;
                core:principal "1000.00"^^xsd:decimal ;
                core:currency "EUR" ;
                core:term 12 ;
                core:rate "1.00"^^xsd:decimal .
        }
        """
        res_l2 = call_tool("execute_sparql", {"query": t2_contradiction}, req_id=3)
        assert res_l2.get("status") == "REJECTED" and res_l2.get("error_type") == "LogicalInconsistency", f"Test 2.2 Failed: {res_l2}"
        print("  ✔ Layer 2 (HermiT): Disjointness clash intercepted & rolled back.")

        # -------------------------------------------------------------
        # TEST 2.3: Layer 3 — SHACL-AF SPARQL Rule Inference
        # -------------------------------------------------------------
        t3_rule = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:Loan_HighRate_L3 a core:PersonalLoan ;
                core:principal "25000.00"^^xsd:decimal ;
                core:currency "EUR" ;
                core:term 48 ;
                core:rate "15.00"^^xsd:decimal .
        }
        """
        res_l3 = call_tool("execute_sparql", {"query": t3_rule}, req_id=4)
        assert res_l3.get("status") == "SUCCESS", f"Test 2.3 Failed: {res_l3}"

        g_l3 = rdflib.Graph().parse(DATA_FILE, format="xml")
        assert (CORE.Loan_HighRate_L3, RDF.type, CORE.HighRiskProduct) in g_l3, "Test 2.3 Failed: core:HighRiskProduct not materialized"
        print("  ✔ Layer 3 (SHACL-AF): Rate > 10.0% materialized core:HighRiskProduct.")

        # -------------------------------------------------------------
        # TEST 2.4: Layer 4 — SKOS Missing-Label Rejection & Taxonomy Gate
        # -------------------------------------------------------------
        # 2.4a: Negative test - Unlabelled concept MUST be rejected
        t4_bad_skos = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:PeerToPeerLending a skos:Concept .
            core:Loan_P2P_BadSKOS a core:PersonalLoan ;
                core:loanCategory core:PeerToPeerLending ;
                core:principal "10000.00"^^xsd:decimal ;
                core:currency "EUR" ;
                core:term 24 ;
                core:rate "4.50"^^xsd:decimal .
        }
        """
        res_l4_bad = call_tool("execute_sparql", {"query": t4_bad_skos}, req_id=5)
        assert res_l4_bad.get("status") == "REJECTED", f"Test 2.4a Failed: Expected rejection, got {res_l4_bad}"
        assert res_l4_bad.get("error_type") == "SKOSTerminologyError", f"Test 2.4a Failed: Expected SKOSTerminologyError, got {res_l4_bad.get('error_type')}"
        assert "PeerToPeerLending" in res_l4_bad.get("details", ""), "Test 2.4a Failed: Error details did not mention offending concept."
        print("  ✔ Layer 4a (SKOS Negative): Unlabelled concept 'PeerToPeerLending' blocked with SKOSTerminologyError.")

        # 2.4b: Positive test - Concept with multilingual prefLabels MUST pass
        t4_good_skos = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:PeerToPeerLending a skos:Concept ;
                skos:prefLabel "Peer-to-Peer Lending"@en , "Préstamo P2P"@es .
            core:Loan_P2P_GoodSKOS a core:PersonalLoan ;
                core:loanCategory core:PeerToPeerLending ;
                core:principal "10000.00"^^xsd:decimal ;
                core:currency "EUR" ;
                core:term 24 ;
                core:rate "4.50"^^xsd:decimal .
        }
        """
        res_l4_good = call_tool("execute_sparql", {"query": t4_good_skos}, req_id=6)
        assert res_l4_good.get("status") == "SUCCESS", f"Test 2.4b Failed: Valid SKOS concept was rejected: {res_l4_good}"
        print("  ✔ Layer 4b (SKOS Positive): Concept with @en and @es prefLabels successfully committed.")

        # -------------------------------------------------------------
        # TEST 2.5: Layer 5 — PROV-O Dual-Stamping & Forensic Lineage Assertion
        # -------------------------------------------------------------
        t5_spoofed_prov = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:Loan_SpoofedAudit_03 a core:PersonalLoan ;
                core:principal "15000.00"^^xsd:decimal ;
                core:currency "EUR" ;
                core:term 36 ;
                core:rate "5.00"^^xsd:decimal ;
                prov:wasAttributedTo "Executive_Admin_Bypass" ;
                prov:generatedAtTime "2020-01-01T00:00:00Z"^^xsd:dateTime .
        }
        """
        res_l5 = call_tool("execute_sparql", {"query": t5_spoofed_prov}, req_id=7)
        assert res_l5.get("status") == "SUCCESS", f"Test 2.5 Failed: Transaction was not accepted: {res_l5}"

        # Inspect core.owl on disk to verify dual-stamping
        g_l5 = rdflib.Graph().parse(DATA_FILE, format="xml")
        loan_ref = CORE.Loan_SpoofedAudit_03

        attributions = [str(o) for o in g_l5.objects(loan_ref, PROV.wasAttributedTo)]
        timestamps = [str(o) for o in g_l5.objects(loan_ref, PROV.generatedAtTime)]

        # 1. Check Dual Attributions (Spoofed literal + Verified System Agent URI)
        assert "Executive_Admin_Bypass" in attributions, "Test 2.5 Failed: Spoofed attribution literal missing from graph."
        assert str(CORE.MCP_Autonomous_Agent) in attributions, "Test 2.5 Failed: Verified system agent URI was not stamped."
        assert len(attributions) >= 2, f"Test 2.5 Failed: Expected >=2 attributions for dual-audit, found: {attributions}"

        # 2. Check Dual Timestamps (Backdated 2020 timestamp + Live System ISO timestamp)
        has_backdated_time = any("2020-01-01" in t for t in timestamps)
        has_current_time = any("2020-01-01" not in t for t in timestamps)
        assert has_backdated_time, "Test 2.5 Failed: Backdated user timestamp missing."
        assert has_current_time, "Test 2.5 Failed: Real-time system execution timestamp missing."
        assert len(timestamps) >= 2, f"Test 2.5 Failed: Expected >=2 timestamps for dual-audit, found: {timestamps}"

        print(f"  ✔ Layer 5 (PROV-O Dual-Stamp): Verified forensic dual-attribution {attributions} and dual-timestamps {timestamps}.")

    finally:
        proc.terminate()


# =====================================================================
# Execution Entry Point
# =====================================================================
if __name__ == "__main__":
    print("================================================================")
    print("🧪 EXECUTING FULL NEURO-SYMBOLIC 5-LAYER TEST SUITE")
    print("================================================================\n")
    run_stage_1_static_tests()
    run_stage_2_mcp_integration_tests()
    print("\n================================================================")
    print("🎉 ALL 5 LAYERS (INCLUDING SKOS & PROV-O FORENSICS) VERIFIED.")
    print("================================================================")