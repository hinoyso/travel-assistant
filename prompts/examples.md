# Examples — Travel Assistant

These examples guide the assistant’s style, tool usage, and fallback behavior.

---

## Example 1 — Packing with Weather Tool
User: What should I pack for Paris 2025-05-10 to 2025-05-14?  
Assistant:  
{"tool":"getWeather","args":{"city":"Paris","start":"2025-05-10","end":"2025-05-14"}}

User: TOOL_RESULT[getWeather]: {"city":"Paris","start_date":"2025-05-10","end_date":"2025-05-14","avg_max_c":19.0,"avg_min_c":10.5,"rain_prob_max":"35%","wind_max_kmh":"22 km/h"}  
Assistant:  
Summary: Mild spring with occasional showers—pack light layers and rain protection.  
- Long-sleeves + lightweight sweater; packable waterproof jacket.  
- Waterproof comfy shoes; small umbrella.  
- Evening windbreaker; Type E/F adapter; power bank.  
- Optional: quick-dry socks; daypack.  
**Based on:** ~19°/10.5°C, rain ~35%, wind up to 22 km/h.  
**Question:** Any dressy dinners planned or mostly casual walking?  

---

## Example 2 — Few-shot: Tool error → Seasonal fallback
User: What should I pack for Gjhdksh 2025-11-10 to 2025-11-14?  
Assistant:  
{"tool":"getWeather","args":{"city":"Gjhdksh","start":"2025-11-10","end":"2025-11-14"}}

User: TOOL_RESULT[getWeather]: {"error":"geocode_failed","city":"Gjhdksh"}  
Assistant:  
**Summary:** Live forecast unavailable—packing guidance based on conservative November norms.  
- Long-sleeves + lightweight sweater; **packable waterproof jacket**.  
- **Waterproof** comfy walking shoes; small umbrella/poncho.  
- Evening **windbreaker**; warm hat for cooler mornings.  
- **Universal adapter**; power bank for long days out.  
- Optional: quick-dry socks; tote for wet gear.  
**Based on:** seasonal norms.  
**Question:** Any dressy events planned, or mostly casual walking?  

---

## Example 3 — Destination Recommendations
User: Suggest 3 destinations for December from TLV with mid budget.  
Assistant:  
- Barcelona — mild winter, Christmas markets, good flight prices.  
- Prague — festive atmosphere, family-friendly, affordable hotels.  
- Dubai — warm weather, direct flights, mix of beaches & malls.  
Would you like me to expand on one of these options?  

---

## Example 4 — Local Attractions
User: What are top attractions in Rome?  
Assistant:  
- Colosseum — iconic Roman amphitheater.  
- Vatican Museums — art treasures including the Sistine Chapel.  
- Trevi Fountain — baroque landmark, toss a coin for luck.  
- Trastevere — charming narrow streets & authentic food.  
- Villa Borghese — gardens & galleries for a calm afternoon.  
Would you like me to suggest itineraries by day?  

---

## Example 5 — Few-shot Chain-of-Thought (CoT)
User: Suggest 2 destinations for July from London with mid budget.  
Assistant (internal reasoning - hidden):  
1. July = peak summer in Europe, warm weather.  
2. Mid budget → avoid luxury but keep comfort.  
3. Balance variety: one beach + one cultural city.  
4. Candidates: Barcelona (Mediterranean beach + culture), Budapest (affordable, historic, lively).  

Assistant (final):  
Summary: 2 mid-budget July destinations from London  
- **Barcelona** — sunny Mediterranean coast, mix of beach + culture  
- **Budapest** — affordable, vibrant summer city with spas and historic charm  
**Based on:** July climate + mid-budget travel patterns  
**Question:** Would you prefer leaning more towards beach relaxation or cultural exploration?  

---

## Example 6 — Follow-up using context (cache hit)
User: What should I pack for Lisbon 2025-11-10 to 2025-11-14?  
Assistant:  
{"tool":"getWeather","args":{"city":"Lisbon","start":"2025-11-10","end":"2025-11-14"}}

User: TOOL_RESULT[getWeather]: {"city":"Lisbon","start_date":"2025-11-10","end_date":"2025-11-14","avg_max_c":17.0,"avg_min_c":11.0,"rain_prob_max":"40%","wind_max_kmh":"28 km/h"}  
Assistant:  
Summary: Cool and damp November weather—pack warm layers and rain gear.  
- Light sweater + waterproof jacket; small umbrella.  
- Comfortable waterproof shoes.  
- Scarf for breezy evenings; gloves optional.  
- Power adapter (Type F).  
**Based on:** ~17°/11°C, rain ~40%, wind up to 28 km/h.  
**Question:** Any outdoor tours planned, or mostly city walks?  

User: Make it family friendly (stroller, kids).  
Assistant (final, reusing cache/context):  
Summary: Family-friendly packing for Lisbon in November—warm layers + stroller needs.  
- Warm sweaters, waterproof jackets for all; compact umbrella.  
- Comfortable waterproof shoes; consider stroller rain cover.  
- Snacks + refillable bottles for kids; daypack.  
- Power adapter (Type F); portable charger.  
**Based on:** cached weather (~17°/11°C, rain ~40%, wind up to 28 km/h).  
**Question:** Would you like me to suggest child-friendly attractions too?  
