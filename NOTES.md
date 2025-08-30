# Prompt & System Design Notes

## Query Types Covered
- **Destination recommendations** → direct final output (no tools).
- **Local attractions** → direct final output (no tools).
- **Packing suggestions** → uses weather tool getWeather(city, start, end); falls back to seasonal norms on error.

## Prompts
**System:** Persona = helpful, concise, structured; respects context; avoids hallucinations.  
**Developer:**  
- **Output format:** Summary → 3–6 bullets → Based on: … → one short follow-up.  
- **Units:** metric only (°C, km/h).  
- **Tool-call protocol:** When a tool is needed, first response is JSON only:
  {"tool":"getWeather","args":{"city":"...", "start":"YYYY-MM-DD", "end":"YYYY-MM-DD"}}
  No extra text/markdown. If tool data is present, ground the answer in it; otherwise use seasonal norms.  
- **Fallback rule:** If tool fails, immediately produce a full answer; end with:  
  Based on: seasonal norms for <Month or Mon–Mon>.  
- **Destinations/Attractions:** Explicitly do not call tools; return { "final": ... } style answers.

## Examples (Few-shot)
- Added examples for: destinations, attractions, packing with tool success, packing with tool error (seasonal fallback).  
- Includes an error example to reinforce the fallback behavior.

## Tooling
- External API: Open-Meteo (Geocoding + Forecast).  
- Cache: In-memory TOOL_CACHE keyed by (tool, args) to reuse results on follow-ups.  
- Mixed JSON guard: If the LLM mixes JSON + text, we nudge it to resend JSON-only.

## Conversation & Context
- history keeps prior turns so follow-ups like “make it family friendly” reuse context.  
- After tool execution, we re-call the LLM with:
  - an assistant message echoing the tool call, and
  - a user message TOOL_RESULT[...] containing the tool output + instruction to finalize.

## Error Handling
- geocode_failed or forecast_failed → seasonal norms (month-aware), still deliver a full packing list.  
- Missing critical args (e.g., dates) → single clarifying question.  
- Unknown tools → return structured error; current code only supports getWeather.
- If requested dates are more than 16 days ahead, the assistant skips the weather tool entirely, explicitly says “I wasn’t able to get a real forecast”, and bases guidance only on seasonal norms.

## Logging & Transcripts
- Commands:
  - /log <path> → append (adds --- + Session started: ...).  
  - /log! <path> → overwrite and start fresh.  
  - /stoplog → stop logging.  
- Transcript structure: User → Assistant (first response – JSON) → TOOL_RESULT[...] → Assistant (final).

## Testing Checklist
- Destinations: “Suggest 3 destinations for January from Rome with high budget.” → 3 concise picks + follow-up.  
- Attractions: “Give me some good attractions in Tokyo.” → 5–7 bullets + follow-up.  
- Packing (success): Near-future dates → JSON tool-call → grounded final with Based on: temps/rain/wind.  
- Packing (error): Fake city or far-future dates → tool error → seasonal fallback final.  
- Follow-up reuse: Ask “Make it family-friendly / stroller” → no repeat tool call (cache hit logged).

## Possible Next Steps
- Add getAttractions(city) or flight-price stubs (optional).  
- History truncation or RAG if context grows long.

## Chain-of-Thought Prompting
I explicitly instructed the model in `developer.md` to "think step by step internally (chain of thought) before producing the final answer, but never reveal these steps."  

To validate the effect, I tested the system **with and without** this instruction using the three query types:
- **Destination recommendations** → no major difference (simple recall task).
- **Local attractions** → with CoT the model produced a more balanced, diverse list (cultural + modern + food).
- **Packing (tool call + error fallback)** → with CoT the model’s output was more consistent: always formatted as Summary → bullets → Based on → follow-up, and correctly used seasonal norms when live data failed.

Conclusion: the chain-of-thought instruction improved **structure, reliability, and consistency**, especially in multi-step reasoning queries such as packing lists.

