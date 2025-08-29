import requests, re, datetime as dt, json, sys, os
TOOL_CACHE = {}  # simple in-memory cache for tool results

def extract_json_block(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else None

# --- simple transcript logger (append sessions instead of overwrite) ---
LOG_PATH = None

def set_log(path: str, mode: str = "append"):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    global LOG_PATH
    LOG_PATH = path

    # If overwriting or file doesn't exist, create header once
    if mode == "overwrite" or not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Transcript — {os.path.basename(path)}\n")

    # Always append a new session divider
    import datetime as dt
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n---\n## Session started: {stamp}\n\n")

def stop_log():
    global LOG_PATH
    LOG_PATH = None

def write_log(line: str):
    if LOG_PATH:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")


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

def parse_tool_or_final(text: str):
    s = text.strip()
    # strip code fences if present
    if s.startswith("```"):
        # remove leading ```json / ``` and trailing ```
        s = s.lstrip("`")
        s = s[s.find("\n")+1:] if "\n" in s else s  # drop the first line (``` or ```json)
        if s.endswith("```"):
            s = s[: -3]
        s = s.strip()
    # try JSON
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            if "tool" in data and "args" in data:
                return ("tool_call", data["tool"], data["args"])
            if "final" in data:
                return ("final", data["final"])
    except Exception:
        pass
    return ("final", text)  # treat as final NL if not clean JSON

# --- run a tool by name ---
def run_tool(tool_name: str, args: dict):
    key = (tool_name, json.dumps(args, sort_keys=True))
    if key in TOOL_CACHE:
        # optional: log a compact note instead of repeating big blocks
        write_log(f"**TOOL_RESULT[{tool_name}] (cache):**\n```json\n{json.dumps(TOOL_CACHE[key])}\n```")
        return TOOL_CACHE[key]

    if tool_name == "getWeather":
        city  = args.get("city")
        start = args.get("start")
        end   = args.get("end")
        if not (city and start and end):
            res = {"error": "missing_args", "required": ["city","start","end"]}
            TOOL_CACHE[key] = res
            return res
        res = get_weather(city, start, end)
        TOOL_CACHE[key] = res
        return res

    res = {"error": "unknown_tool", "tool": tool_name}
    TOOL_CACHE[key] = res
    return res



# Helper: label the month(s) from the user's dates (e.g., "November" or "Aug–Sep")
def month_label(start_iso: str, end_iso: str) -> str:
    """
    Returns 'November' if both dates in same month, else 'Aug–Sep'.
    Falls back to 'that time of year' on parse issues.
    """
    try:
        s = dt.date.fromisoformat(start_iso)
        e = dt.date.fromisoformat(end_iso)
        if s.month == e.month:
            return s.strftime("%B")
        return f"{s.strftime('%b')}–{e.strftime('%b')}"
    except Exception:
        return "that time of year"


def chat_turn(user_msg: str):
    messages = [
        {"role": "system",    "content": SYSTEM},
        {"role": "developer", "content": DEVELOPER},
        {"role": "user",      "content": "Guidance examples:\n" + EXAMPLES},
        *history,
        {"role": "user",      "content": user_msg},
    ]
        # 1. First call to LLM
    first = call_llm(messages)
    kind, *rest = parse_tool_or_final(first)   # <-- parse first, then use 'kind'

    # Clarify protocol: if first answer is final and user_msg is ambiguous (destinations)
    if kind == "final" and ("destination" in user_msg.lower() or "suggest" in user_msg.lower()):
        missing_month = not re.search(
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})",
            user_msg.lower()
        )
        missing_from = not re.search(r"\bfrom\s+[A-Z]", user_msg)
        if missing_month or missing_from:
            return "From which city are you departing, and for what month or season?"

    # 2. If the model mixed JSON + extra text, nudge again
    json_block = extract_json_block(first)
    if json_block and not first.strip() == json_block.strip():
        print("[DEBUG] Mixed JSON+text detected, nudging model again")
        messages.append({"role":"user","content":
            "Reminder: When a tool is needed, your FIRST response must be JSON ONLY. "
            "No natural language, no preamble, no 'please wait' text. Try again."
        })
        first = call_llm(messages)
        kind, *rest = parse_tool_or_final(first)

    # 3. Nudge once if it's a weather/packing intent and model ignored JSON-only rule
    if kind == "final" and not first.strip().startswith("{") and needs_weather(user_msg):
        messages.append({"role": "user", "content":
            "Protocol reminder: Your FIRST response must be JSON per TOOL-CALL PROTOCOL. "
            "Either {\"tool\":...} or {\"final\":...}. No natural language."
        })
        first = call_llm(messages)
        kind, *rest = parse_tool_or_final(first)

    # 4. Log first response ONLY if it's JSON (tool-call)
    if first.strip().startswith("{"):
        write_log("**Assistant (first response - JSON):**\n```json\n" + first + "\n```")
    print("[DEBUG] First model response:", first)

    # 5. Allow up to 2 tool calls
    for _ in range(2):
        if kind == "tool_call":
            tool_name, args = rest

            # --- cache key for this tool+args ---
            key = (tool_name, json.dumps(args, sort_keys=True))
            cache_hit = key in TOOL_CACHE

            # --- get result (from cache or by running the tool) ---
            if cache_hit:
                tool_result = TOOL_CACHE[key]
            else:
                tool_result = run_tool(tool_name, args)
                TOOL_CACHE[key] = tool_result

            # --- console debug ---
            print("[DEBUG] Model requested tool:", tool_name, "args:", args)
            print("[DEBUG] Tool result:", tool_result)

            # --- transcript logging (short on cache hits) ---
            if cache_hit:
                write_log(f"**Assistant reused prior weather (cache hit)** for `{tool_name}` args:\n```json\n{json.dumps(args, sort_keys=True)}\n```")
            else:
                write_log(f"**Assistant requested tool:** `{tool_name}` args:\n```json\n{json.dumps(args, sort_keys=True)}\n```")
                write_log(f"**TOOL_RESULT[{tool_name}]:**\n```json\n{json.dumps(tool_result)}\n```")

            # --- return tool result to the model; ask for final answer ---
            messages += [
                {"role": "assistant", "content": json.dumps({"tool": tool_name, "args": args})},
            ]

            if isinstance(tool_result, dict) and tool_result.get("error"):
                month_hint = month_label(args.get("start", ""), args.get("end", ""))
                if tool_result.get("error") == "geocode_failed":
                    city_hint = "this location"
                else:
                    city_hint = args.get("city") or "this location"

                messages.append({"role": "user", "content":
                    f"TOOL_RESULT[{tool_name}]: {json.dumps(tool_result)}\n"
                    f"Live forecast was unavailable. Fall back to typical seasonal norms for {city_hint} in {month_hint}. "
                    "Produce the FINAL answer now in the OUTPUT FORMAT (Summary → 3–6 bullets → "
                    f"**Based on:** seasonal norms for {month_hint} → one short follow-up). Metric only."
                })
            else:
                messages.append({
                    "role": "user",
                    "content": (
                        f"TOOL_RESULT[{tool_name}]: {json.dumps(tool_result)}\n"
                        "You now have the tool result. DO NOT wait. Produce the FINAL answer immediately "
                        "following the OUTPUT FORMAT (Summary → 3–6 bullets → Based on → one short follow-up). "
                        "No JSON this time, only the final text."
                    )
                })

            nxt = call_llm(messages)

            if nxt.strip().startswith("{"):
                write_log("**Assistant (intermediate - JSON):**\n```json\n" + nxt + "\n```")

            kind, *rest = parse_tool_or_final(nxt)
            if kind == "final":
                final_text = rest[0]
                write_log(f"**Assistant (final):**\n{final_text}\n")
                return final_text
            # else: another tool_call → loop again

        else:
            # Already a final answer (no tool needed)
            final_text = rest[0]
            write_log(f"**Assistant (final):**\n{final_text}\n")
            return final_text

    # 6. Safety fallback if tool chain exceeded allowed hops
    final_text = "I couldn’t complete the tool sequence. Please try again with clearer details."
    write_log(f"**Assistant (final):**\n{final_text}\n")
    return final_text


def run():
    print("Travel Assistant (type 'exit' to quit)")
    last_console_reply = None
    while True:
        try:
            user = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        # --- transcript logging commands ---
        if user.startswith("/log! "):  # overwrite & start fresh
            path = user.split(" ", 1)[1].strip()
            set_log(path, mode="overwrite")
            print(f"[LOGGING] Overwriting transcript at {path}")
            continue

        if user.startswith("/log "):   # append a new session
            path = user.split(" ", 1)[1].strip()
            set_log(path, mode="append")
            print(f"[LOGGING] Appending transcript to {path}")
            continue

        if user.strip() == "/stoplog":
            stop_log()
            print("[LOGGING] Stopped logging.")
            continue
        # -----------------------------------

        if user.strip().lower() == "exit":
            print("Bye!")
            break

        # log user turn and run one chat turn (chat_turn logs assistant final)
        write_log(f"**User:** {user}")
        reply = chat_turn(user)

        # keep context for follow-ups
        # keep context for follow-ups
        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": reply})

        # print one clean response per turn
        if reply != last_console_reply:
            print("\n" + reply + "\n")
            last_console_reply = reply




if __name__ == "__main__":
    run()
