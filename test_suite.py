import subprocess
import json
import os
import sys
import rdflib
import pyshacl

DATA_FILE = "core.owl"
SHAPES_FILE = "shapes.ttl"

# =====================================================================
# STAGE 1: Static Schema & Shape Unit Test
# =====================================================================
def run_stage_1_static_tests():
    print("▶ STAGE 1: Static File & SHACL Schema Validation")
    
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

    print("  ✔ Base core.owl satisfies all shapes.ttl constraints.\n")


# =====================================================================
# STAGE 2: Dynamic MCP Server & Guardrail Integration Test
# =====================================================================
def run_stage_2_mcp_integration_tests():
    print("▶ STAGE 2: Live MCP Server Integration & Guardrail Test")

    proc = subprocess.Popen(
        [sys.executable, "-u", "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,  # Stream server logs and Java output directly to terminal
        text=True,
        bufsize=1
    )

    def send_request(method: str, params: dict = None, req_id: int = 1):
        """Sends a JSON-RPC request and waits for a response."""
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
        """Sends a JSON-RPC notification (does NOT wait for a response)."""
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
        # Handshake: Request followed by Notification
        send_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "TestSuite"}}, req_id=0)
        send_notification("notifications/initialized")

        # 2.1 Happy Path
        t1 = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:Loan_Valid_99 a core:PersonalLoan ;
                core:principal "18000.00"^^xsd:decimal ;
                core:currency "EUR" ;
                core:term 60 ;
                core:rate "5.50"^^xsd:decimal .
        }
        """
        res1 = call_tool("execute_sparql", {"query": t1}, req_id=1)
        assert res1.get("status") == "SUCCESS", f"Test 2.1 Failed: {res1}"
        print("  ✔ 2.1 Happy Path: Valid transaction verified and committed.")

        # 2.2 SHACL Violation Interception
        t2 = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:Loan_Invalid_99 a core:PersonalLoan ;
                core:principal "5000.00"^^xsd:decimal ;
                core:currency "DOGE" ;
                core:term 300 ;
                core:rate "5.50"^^xsd:decimal .
        }
        """
        res2 = call_tool("execute_sparql", {"query": t2}, req_id=2)
        assert res2.get("status") == "REJECTED" and res2.get("error_type") == "SHACLShapeViolation", f"Test 2.2 Failed: {res2}"
        print("  ✔ 2.2 SHACL Rejection: Invalid currency and term blocked before HermiT.")

        # 2.3 DL Contradiction Interception
        call_tool("add_subclass", {"new_class": "DepositAccount", "parent_class": "FinancialProduct"}, req_id=3)
        t3 = """
        PREFIX core: <http://banco.es/ontologies/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA {
            core:PersonalLoan owl:disjointWith core:DepositAccount .
            core:Prod_Clash_99 a core:PersonalLoan, core:DepositAccount ;
                core:principal "1000.00"^^xsd:decimal ;
                core:currency "EUR" ;
                core:term 12 ;
                core:rate "1.00"^^xsd:decimal .
        }
        """
        res3 = call_tool("execute_sparql", {"query": t3}, req_id=4)
        assert res3.get("status") == "REJECTED" and res3.get("error_type") == "LogicalInconsistency", f"Test 2.3 Failed: {res3}"
        print("  ✔ 2.3 HermiT Rejection: Disjointness clash intercepted and rolled back.")

    finally:
        proc.terminate()


# =====================================================================
# Execution Entry Point
# =====================================================================
if __name__ == "__main__":
    print("================================================================")
    print("🧪 EXECUTING FULL NEURO-SYMBOLIC TEST SUITE")
    print("================================================================\n")
    run_stage_1_static_tests()
    run_stage_2_mcp_integration_tests()
    print("================================================================")
    print("🎉 ALL TESTS PASSED: Schema, Server & Guardrails are healthy.")
    print("================================================================")