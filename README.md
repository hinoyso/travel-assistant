# Travel Assistant

A simple CLI-based travel assistant that uses an LLM (Ollama) + external weather API.

## Features
- Handles 3 query types: destinations, packing, attractions
- Maintains conversation context
- Integrates with Open-Meteo weather API
- Error handling + fallbacks

## How to Run
1. Install Python 3.9+  
2. Install [Ollama](https://ollama.com) and pull model:  
   ```bash
   ollama pull llama3.1
   ollama serve
