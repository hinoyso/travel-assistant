# chat_cli.py
import requests, re, datetime as dt, json, sys, os

# --- Load prompts from files ---
def read_prompt(path):
    try:
        return open(path, "r", encoding="utf-8").read()
    except Exception as e:
        print(f"[PROMPT ERROR] Could not read {path}: {e}")
        return ""

SYSTEM = read_prompt("prompts/system.md")
DEVELOPER = read_prompt("prompts/developer.md")
EXAMPLES = read_prompt("prompts/examples.md")

history = []  # stores prior turns so the model keeps context

# --- LLM call (Ollama local) ---
def call_llm(messages):
    url = "http://localhost:11434/api/chat"
    payload = {"model": "llama3.1", "messages": messages, "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        if r.status_code != 200:
            print("\n[LLM ERROR]", r.status_code, r.text, "\n")
            return "I hit an issue contacting the local LLM. Is Ollama running?"
        data = r.json()
        # Typical Ollama response
        if "message" in data and "content" in data["message"]:
            return data["message"]["content"]
        # Fallback if format differs
        if "choices" in data and data["choices"]:
            return data["choices"][0].get("message", {}).get("content", "")
        print("\n[LLM WARN] Unexpected response format:\n", json.dumps(data, indent=2), "\n")
        return "I got an unexpected response format from the LLM."
    except Exception as e:
        print("\n[LLM EXCEPTION]", e, "\n")
        return "I couldn’t reach the local LLM service. Is `ollama serve` running?"

# --- Simple policy: do we need weather? ---
MONTH_WORDS = r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december"

def needs_weather(msg: str) -> bool:
    m1 = re.search(r'(pack|packing|what to wear|weather|rain|hot|cold|temperature)', msg.lower())
    m2 = re.search(rf'({MONTH_WORDS}|\d{{4}}|today|tomorrow|next week|next month|this weekend|season)', msg.lower())
    return bool(m1 and m2)

def extract_city(msg: str):
    # Very naive: look for "in <City>" or "for <City>"
    m = re.search(r'\b(?:in|for)\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)\b', msg)
    return m.group(1) if m else None

def extract_date_range_or_default(msg: str):
    """
    Try to parse YYYY-MM-DD in text; if nothing found, default to [today, today+3].
    (Open-Meteo can forecast ~16 days ahead; for far-future months we'll still default
    to near-term forecast just to demo the tool, and the assistant will note uncertainty.)
    """
    # yyyy-mm-dd
    d = re.findall(r'(\d{4}-\d{2}-\d{2})', msg)
    if len(d) >= 2:
        return d[0], d[1]
    if len(d) == 1:
        start = dt.date.fromisoformat(d[0])
        return d[0], str(start + dt.timedelta(days=3))
    # Default: next 3 days
    today = dt.date.today()
    return str(today), str(today + dt.timedelta(days=3))

# --- Weather tool (Open-Meteo: free, no key) ---
def get_weather(city: str, start: str, end: str):
    try:
        g = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en"},
            timeout=30
        ).json()
        if not g.get("results"):
            return {"error": "geocode_failed", "city": city}

        lat = g["results"][0]["latitude"]
        lon = g["results"][0]["longitude"]

        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start,
                "end_date": end,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
                "timezone": "auto",
            },
            timeout=30
        ).json()

        daily = w.get("daily")
        if not daily:
            return {"error": "forecast_failed", "city": city, "lat": lat, "lon": lon}

        def avg(xs): return round(sum(xs) / max(1, len(xs)), 1)

        tmax = avg(daily.get("temperature_2m_max", []))
        tmin = avg(daily.get("temperature_2m_min", []))
        rain = max(daily.get("precipitation_probability_max", [0])) if daily.get("precipitation_probability_max") else None
        wind = max(daily.get("wind_speed_10m_max", [0])) if daily.get("wind_speed_10m_max") else None

        return {
            "city": city,
            "start_date": start,
            "end_date": end,
            "avg_max_c": tmax,
            "avg_min_c": tmin,
            "rain_prob_max": f"{rain}%" if rain is not None else "n/a",
            "wind_max_kmh": f"{wind} km/h" if wind is not None else "n/a"
        }
    except Exception as e:
        return {"error": f"exception: {e.__class__.__name__}", "city": city}

def run():
    print("Travel Assistant (type 'exit' to quit)")
    while True:
        try:
            user = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if user.strip().lower() == "exit":
            print("Bye!")
            break

        # Collect tool messages (as user-visible TOOL lines for simplicity)
        tool_lines = []
        if needs_weather(user):
            city = extract_city(user) or "Lisbon"  # fallback city
            start, end = extract_date_range_or_default(user)
            wx = get_weather(city, start, end)
            # Inject tool data as a line the model can read (per developer.md)
            tool_lines.append({"role": "user", "content": f"TOOL[getWeather]: {json.dumps(wx)}"})

        # Build the message stack
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "developer", "content": DEVELOPER},
            {"role": "user", "content": "Guidance examples:\n" + EXAMPLES},
            *history,
            *tool_lines,
            {"role": "user", "content": user}
        ]

        reply = call_llm(messages)

        # Save turn to history
        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": reply})

        print(reply, "\n")

if __name__ == "__main__":
    run()
