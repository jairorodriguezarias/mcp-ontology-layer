# agente.py
import subprocess
import json
import urllib.request
import sys

MODEL = "glm-5.2:cloud"
OLLAMA_URL = "http://localhost:11434/api/chat"

class MCPClientProcess:
    def __init__(self, server_script="server.py"):
        self.proc = subprocess.Popen(
            [sys.executable, server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.req_id = 1

    def send_request(self, method, params=None):
        payload = {
            "jsonrpc": "2.0",
            "id": self.req_id,
            "method": method
        }
        if params is not None:
            payload["params"] = params
            
        self.req_id += 1
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        
        line = self.proc.stdout.readline()
        if not line:
            err_output = self.proc.stderr.read()
            raise RuntimeError(f"Subprocess server.py exited unexpectedly:\n{err_output}")
        return json.loads(line)

    def close(self):
        self.proc.terminate()

def chat_ollama(messages, tools):
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "options": {
            "temperature": 0
        }
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print(f"--- Starting Semantic Agent (Model: {MODEL}) ---")
    print("Connecting to local MCP Server (server.py)...")
    mcp = MCPClientProcess()

    # 1. MCP Handshake
    mcp.send_request("initialize", {"protocolVersion": "2024-11-05"})

    # 2. Dynamic Tool Discovery
    mcp_tools_res = mcp.send_request("tools/list")
    raw_tools = mcp_tools_res.get("result", {}).get("tools", [])

    tools = []
    for t in raw_tools:
        tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["inputSchema"]
            }
        })

    tool_names = [t["function"]["name"] for t in tools]
    print(f"Discovered MCP Tools: {tool_names}\n")

    # 3. Agent Execution Goal
    prompt = (
        "1. Add 'PrestamoHipotecario' as a subclass of 'Loan'.\n"
        "2. Create an individual 'Hipoteca_Fija_001' of type 'PrestamoHipotecario'.\n"
        "3. Check the ontology consistency using the DL reasoner.\n"
        "4. Export an interactive visualization of the knowledge graph to 'graph.html'."
    )
    print(f"Agent Goal:\n{prompt}\n" + "-" * 50)

    messages = [
        {
            "role": "system",
            "content": "You are an autonomous semantic web engineer. Use the available MCP tools to inspect, modify, reason, and visualize the banking ontology."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    while True:
        response = chat_ollama(messages, tools)
        message = response.get("message", {})
        messages.append(message)

        if message.get("content"):
            print(f"\n[Agent Response]\n{message['content']}")

        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            break

        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            fn_name = function.get("name")
            fn_args = function.get("arguments", {})

            print(f"\n-> [MCP Request] Calling: {fn_name}({fn_args})")
            tool_response = mcp.send_request("tools/call", {
                "name": fn_name,
                "arguments": fn_args
            })

            content_blocks = tool_response.get("result", {}).get("content", [])
            output_text = " ".join([b.get("text", "") for b in content_blocks if b.get("type") == "text"])
            print(f"<- [MCP Response] {output_text}")

            messages.append({
                "role": "tool",
                "content": output_text
            })

    mcp.close()
    print("\n--- Pipeline Completed Successfully ---")

if __name__ == "__main__":
    main()