# Local MCP Semantic Agent with OWL & Ollama

Arquitectura de ejecucion 100% local en macOS para la manipulacion e inspeccion determinista de ontologias bancarias (OWL/RDF) mediante agentes LLM y el protocolo Model Context Protocol (MCP) implementado sobre STDIO.

## Arquitectura

El flujo desacopla el razonamiento del modelo de la ejecucion del grafo semantico en cuatro componentes:

1. **Agente Orquestador (agente.py):** Inicializa el servidor MCP como subproceso, realiza el handshake JSON-RPC 2.0 y gestiona el ciclo de llamadas de herramientas con Ollama.
2. **Motor LLM (Ollama):** Ejecuta el modelo local (glm-5.2:cloud o qwen2.5-coder) para analizar la peticion y generar los argumentos de ejecucion.
3. **Servidor MCP (server.py):** Procesa solicitudes estandarizadas por entrada y salida estandar (STDIO) y traduce las peticiones a operaciones de libreria.
4. **Capa Semantica (core.owl):** Grafo ontologico en formato RDF/XML manipulado y persistido en disco mediante Owlready2.

## Estructura del Repositorio

* **core.owl:** Ontologia base en formato RDF/XML (Estandar W3C OWL).
* **server.py:** Servidor MCP nativo JSON-RPC 2.0 sobre STDIO.
* **agente.py:** Cliente MCP y bucle de ejecucion conectado a la API de Ollama.
* **requirements.txt:** Dependencias de Python necesarias.
* **.gitignore:** Exclusion de entornos virtuales y temporales.
* **README.md:** Documentacion del proyecto.

## Requisitos Previos

* macOS (compatible con Apple Silicon e Intel)
* Python 3.10 o superior
* Ollama instalado y en ejecucion