import json

# =============================================================================
# TOOL: get_weather
#
# A tool has two parts that must stay in sync:
#
#   1. SCHEMA  — a JSON object the model reads BEFORE the conversation starts.
#                It tells the model: what this tool is called, what it does,
#                and what arguments it needs. The model uses this to decide
#                whether and when to call the tool.
#
#   2. IMPLEMENTATION — the actual Python function that runs when the model
#                       decides to call the tool. The application executes this,
#                       not the model.
#
# REQUEST structure (what you send to the API):
#   {
#     "model": "...",
#     "messages": [...],
#     "tools": [ WEATHER_SCHEMA ]       ← list of tool schemas
#   }
#
# RESPONSE structure (what the model sends back when it wants to call a tool):
#   {
#     "choices": [{
#       "message": {
#         "role": "assistant",
#         "content": null,              ← no text response
#         "tool_calls": [{
#           "id": "call_abc123",
#           "type": "function",
#           "function": {
#             "name": "get_weather",    ← which tool to call
#             "arguments": '{"city": "London", "unit": "celsius"}'  ← as JSON string
#           }
#         }]
#       },
#       "finish_reason": "tool_calls"   ← signals a tool call, not a final answer
#     }]
#   }
#
# After you execute the tool, you send the result back as a new message:
#   {
#     "role": "tool",
#     "tool_call_id": "call_abc123",    ← matches the id from above
#     "content": '{"city": "London", "temperature": 15, "condition": "cloudy"}'
#   }
#
# Then the model reads the result and generates its final text response.
# =============================================================================


# PART 1 — SCHEMA
# This is the contract. The model reads this JSON to understand what the tool
# does and what it needs. Write it like documentation for the model.

WEATHER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Get the current weather for a given city. "
            "Use this when the user asks about weather conditions, temperature, "
            "or what to wear in a specific location."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The name of the city, e.g. 'London' or 'New York'",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit. Defaults to celsius.",
                },
            },
            "required": ["city"],   # unit is optional — model can omit it
        },
    },
}


# PART 2 — IMPLEMENTATION
# This runs in your application when the model outputs a tool_call for get_weather.
# The model never sees this code — it only sees the schema above.
# In production this would call a real weather API (OpenWeatherMap, etc).
# Here we return stubbed data so the flow is testable without an API key.

def get_weather(city: str, unit: str = "celsius") -> dict:
    # stub — replace the body with a real API call when ready
    # the return value must be JSON-serialisable: it goes back to the model as a string
    stub_data = {
        "London":   {"temperature": 15, "condition": "cloudy",  "humidity": 80},
        "New York": {"temperature": 22, "condition": "sunny",   "humidity": 55},
        "Tokyo":    {"temperature": 28, "condition": "humid",   "humidity": 90},
    }
    weather = stub_data.get(city, {"temperature": 20, "condition": "unknown", "humidity": 60})
    return {"city": city, "unit": unit, **weather}


# PART 3 — DISPATCHER
# When the model returns a tool_call, your application gets back a function name
# and a JSON string of arguments. The dispatcher:
#   1. parses the JSON arguments
#   2. routes to the correct function by name
#   3. returns the result as a JSON string (ready to send back to the model)
#
# As you add more tools, you register them here — one place to maintain.

REGISTRY = {
    "get_weather": get_weather,
}


def dispatch(tool_name: str, arguments_json: str) -> str:
    args = json.loads(arguments_json)       # model sends arguments as a JSON string
    fn = REGISTRY.get(tool_name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {tool_name}"})
    result = fn(**args)                     # call the function with unpacked arguments
    return json.dumps(result)               # return result as JSON string to the model
