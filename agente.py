import subprocess
import json
import urllib.request
import sys

MODEL = "glm-5.2:cloud"
OLLAMA_URL = "http://localhost:11434/api/chat"

class MCPClientProcess:
    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.req_id = 1

    def send_request(self, method, params=None):
        payload = {"jsonrpc": "2.0", "id": self.req_id, "method": method}
        if params is not None:
            payload["params"] = params
        self.req_id += 1
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        return json.loads(line)

    def close(self):
        self.proc.terminate()

def chat_ollama(messages, tools):
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "options": {"temperature": 0}
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print(f"Iniciando agente con modelo: {MODEL}")
    print("Conectando con Servidor MCP local (server.py)...")
    mcp = MCPClientProcess()
    
    # 1. Handshake MCP
    mcp.send_request("initialize", {"protocolVersion": "2024-11-05"})
    
    # 2. Descubrir herramientas expuestas por MCP
    mcp_tools_res = mcp.send_request("tools/list")
    tools = []
    for t in mcp_tools_res["result"]["tools"]:
        tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["inputSchema"]
            }
        })
    
    tool_names = [t["function"]["name"] for t in tools]
    print(f"Herramientas descubiertas via MCP: {tool_names}\n")

    # 3. Flujo del Agente
    prompt = (
        "Analiza la ontologia bancaria. Anade la clase PrestamoHipotecario como "
        "subclase de Loan y luego lista las clases para confirmar que se ha guardado."
    )
    print(f"Usuario: {prompt}\n")
    messages = [
        {"role": "system", "content": "Eres un asistente experto en ontologias bancarias. Utiliza tus herramientas para modificar y consultar la ontologia."},
        {"role": "user", "content": prompt}
    ]

    while True:
        res = chat_ollama(messages, tools)
        msg = res["message"]
        messages.append(msg)

        if msg.get("content"):
            agent_text = msg["content"]
            print(f"Agente: {agent_text}")

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            break

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args = tc["function"]["arguments"]
            print(f"\n-> [MCP Request] Ejecutando tool: {fn_name}({fn_args})")
            
            tool_res = mcp.send_request("tools/call", {"name": fn_name, "arguments": fn_args})
            out_text = tool_res["result"]["content"][0]["text"]
            print(f"<- [MCP Response] Resultado: {out_text}\n")
            
            messages.append({"role": "tool", "content": out_text})

    mcp.close()
    print("\nEjecucion completada con exito.")

if __name__ == "__main__":
    main()
