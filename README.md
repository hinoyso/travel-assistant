# Travel Assistant

A simple CLI-based travel assistant that uses an LLM (Ollama) + external weather API.

## Features
- Handles 3 query types: destinations, packing, attractions
- Maintains conversation context across turns
- Integrates with Open-Meteo for live weather
- Graceful error handling + seasonal fallback when API fails
- Transcript logging for demo conversations

## Project Structure
travel-assistant/
├── chat_cli.py        # main CLI entry point
├── prompts/
│   ├── system.md
│   ├── developer.md
│   └── examples.md
├── transcripts/       # demo transcripts (demo1.md, demo2.md, demo3.md)
├── NOTES.md           # design notes
├── README.md          # this file

## Setup
Create a virtual environment and install dependencies:
python3 -m venv .venv
source .venv/bin/activate
pip install requests

## Running
1. Install Ollama and pull the model:
   ollama pull llama3.1
   ollama serve

2. Start the assistant:
   python3 chat_cli.py

3. Type queries, for example:
   - Suggest 3 destinations for December from TLV with mid budget
   - What should I pack for Lisbon 2025-11-10 to 2025-11-14?
   - Give me some good attractions in Tokyo

4. Exit with: exit

## Logging Transcripts
- /log transcripts/demo1.md → append a new session
- /log! transcripts/demo1.md → overwrite and start fresh
- /stoplog → stop logging

## Notes
This repo is structured to demonstrate:
- Prompt design (system.md, developer.md, examples.md)
- Tool integration (getWeather)
- Error handling and fallbacks
- Maintaining conversational context
