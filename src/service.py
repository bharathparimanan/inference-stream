import os
from dotenv import load_dotenv
from together import Together
from tools.weather import WEATHER_SCHEMA, dispatch

load_dotenv()
api_key = os.environ.get("TOGETHER_API_KEY")
model_name = os.environ.get("MODEL_NAME")

# all tool schemas registered here — add more as you build them
TOOLS = [WEATHER_SCHEMA]


def handle_request(messages: list[dict]) -> str:
    client = Together(api_key=api_key)
    response = client.chat.completions.create(model=model_name, messages=messages)
    return response.choices[0].message.content


def handle_request_stream(messages: list[dict]):
    # ==========================================================================
    # PHASE 1 — TOOL LOOP
    # Send messages to the model. If it wants to call a tool, execute it and
    # feed the result back. Repeat until the model stops asking for tools.
    #
    # finish_reason == "tool_calls"  → model wants a tool, not a final answer
    # finish_reason == "stop"        → model is ready to give the final answer
    # ==========================================================================

    client = Together(api_key=api_key)

    while True:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=TOOLS,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            # step 1: append the assistant message that contains the tool_calls
            # the model's tool_call decision must be in the history before the result
            messages.append({
                "role": "assistant",
                "content": choice.message.content,   # usually None
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ],
            })

            # step 2: execute each tool call and append the result
            for tc in choice.message.tool_calls:
                result = dispatch(tc.function.name, tc.function.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,   # must match the id above so the model links them
                    "content": result,        # JSON string returned by dispatch()
                })

            # loop back — the model now reads the tool results and decides
            # whether to call another tool or give the final answer

        else:
            # no more tool calls — exit the loop with the full messages history
            break

    # ==========================================================================
    # PHASE 2 — STREAM FINAL ANSWER
    # Messages now contains the full conversation including all tool results.
    # Make one final streaming call so the answer appears token by token.
    # ==========================================================================

    stream = client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
