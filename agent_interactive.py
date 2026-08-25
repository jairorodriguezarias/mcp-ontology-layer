#agent_interactive.py
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
    print(f"=== Semantic Agent REPL (Model: {MODEL}) ===")
    print("Connecting to local MCP Server (server.py)...")
    mcp = MCPClientProcess()

    # 1. MCP Protocol Handshake
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
    print(f"Discovered Tools: {', '.join(tool_names)}")
    print("Type 'exit', 'quit', or 'q' to end the session.\n" + "=" * 50)

    # 3. Persistent Conversation State
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert semantic web and banking ontology assistant. "
                "Use your tools to query, mutate, reason over, and visualize the local OWL knowledge graph. "
                "Always check with tools before making factual claims about the ontology."
            )
        }
    ]

    try:
        while True:
            user_input = input("\nYou > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting session...")
                break

            messages.append({"role": "user", "content": user_input})

            # Inner ReAct Execution Loop for the current turn
            while True:
                response = chat_ollama(messages, tools)
                message = response.get("message", {})
                messages.append(message)

                tool_calls = message.get("tool_calls", [])
                
                # If no tool call was generated, print the final answer to the user
                if not tool_calls:
                    if message.get("content"):
                        print(f"\nAgent > {message['content']}")
                    break

                # Execute requested tools
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    fn_name = function.get("name")
                    fn_args = function.get("arguments", {})

                    print(f"\n  ⚙️ [MCP Tool Call] {fn_name}({json.dumps(fn_args)})")
                    tool_response = mcp.send_request("tools/call", {
                        "name": fn_name,
                        "arguments": fn_args
                    })

                    content_blocks = tool_response.get("result", {}).get("content", [])
                    output_text = " ".join([
    			json.dumps(b.get("text")) if isinstance(b.get("text"), (list, dict)) 
    			else str(b.get("text", ""))
    			for b in content_blocks if b.get("type") == "text"
		   ])
                    print(f"  📥 [MCP Output] {output_text}")

                    messages.append({
                        "role": "tool",
                        "content": output_text
                    })

    except KeyboardInterrupt:
        print("\nSession interrupted.")
    finally:
        mcp.close()

if __name__ == "__main__":
    main()