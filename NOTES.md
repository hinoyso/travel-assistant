# Prompt Design Notes

## System Prompt
Sets persona: helpful, concise, structured. Priorities: ask clarifying Qs, use tool data first, avoid hallucinations, preserve context.

## Developer Prompt
Defines output format (summary + bullets + "Based on: ...").  
Includes hidden reasoning discipline (think step by step, don’t expose).  
Specifies tool protocol (how to use weather or fallback).

## Examples
Added few-shot examples for destinations, packing, attractions to guide style.

## External API
Integrated Open-Meteo for live forecasts. Injected as TOOL[getWeather]: {...} into the prompt.  
If tool fails, assistant explains and uses seasonal norms.

## Error Handling
- Tool failure → fallback with typical weather.
- Ambiguity → clarifying question.
- Hallucination prevention → assistant admits when it doesn’t know.

## Context
Conversation history preserved in a list. Assistant can handle follow-ups like "make it family friendly" without losing track.

## Edge Cases
- Nonexistent city (graceful fallback).  
- Multiple queries in sequence (context carry).  
- In future: could add truncation or vector DB if history is long.
