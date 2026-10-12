import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import validate
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-5.6-luna"
SYSTEM = "You are a grant-office assistant. Answer the applicant clearly and briefly. Preserve facts from the conversation, distinguish applicant claims from office decisions, and do not invent information."


def load_json(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def usage_tokens(response):
    usage = response.usage
    return getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0


def chat(client, messages):
    response = client.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content, usage_tokens(response)


def compress(client, messages, schema):
    prompt = f'''Compress the conversation into exactly one JSON object matching this JSON Schema:
{json.dumps(schema, ensure_ascii=False)}
Facts are only things the applicant stated. 
Decisions are conclusions or answers already established
 in the conversation. Constraints are conditions about 
 how or when something can happen. Open questions are
  questions the applicant asked that have not been answered.
   Preserve identity, important numbers, missing documents, constraints,
    and unanswered questions when present. 
    Invent nothing. Arrays must be present even when empty.'''
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": prompt}] + messages[1:],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    try:
        state = json.loads(raw)
        validate(state, schema)
        return state, True, usage_tokens(response), None
    except Exception as exc:
        return None, False, usage_tokens(response), str(exc)

def run_script(client, compressed):
    script = load_json("chat_script.json")
    schema = load_json("memory_state.schema.json")
    messages = [{"role": "system", "content": SYSTEM}]
    call_tokens = []
    state = None

    for turn in script["conversation"]:
        if turn == "<compress>":
            if compressed:
                new_state, ok, tokens, error = compress(client, messages, schema)
                if ok:
                    state = new_state
                    messages = [
                        {"role": "system", "content": SYSTEM},
                        {"role": "system", "content": "Compressed conversation state:\n" + json.dumps(state, ensure_ascii=False)},
                    ]
                else:
                    print(f"compression_failed: {error}")
            continue
        messages.append({"role": "user", "content": turn})
        answer, tokens = chat(client, messages)
        call_tokens.append(tokens)
        messages.append({"role": "assistant", "content": answer})

    probes = []
    for probe in script["probes"]:
        probe_messages = messages + [{"role": "user", "content": probe["question"]}]
        answer, _ = chat(client, probe_messages)
        lower = answer.lower()
        retrieved = any(value.lower() in lower for value in probe["expect_contains"])
        probes.append({"id": probe["id"], "retrieved": retrieved, "answer": answer, "tests": probe["tests"]})

    return call_tokens, probes, state


def print_run(label, tokens, probes, state):
    print(f"\n=== {label} ===")
    print("call\tprompt_tokens")
    for i, value in enumerate(tokens, 1):
        print(f"{i}\t{value}")
    print(f"peak\t{max(tokens) if tokens else 0}")
    print(f"total\t{sum(tokens)}")
    print("probes")
    for probe in probes:
        print(f'{probe["id"]}\t{probe["retrieved"]}\t{probe["answer"]}')
    print(f'retrieved={sum(p["retrieved"] for p in probes)}/5')
    if state is not None:
        print("state")
        print(json.dumps(state, ensure_ascii=False, indent=2))


def interactive(client):
    schema = load_json("memory_state.schema.json")
    messages = [{"role": "system", "content": SYSTEM}]
    last_tokens = 0
    print("Interactive mode. Type compress, tokens, or exit.")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            break
        if text.lower() == "tokens":
            print(last_tokens)
            continue
        if text.lower() == "compress":
            state, ok, tokens, error = compress(client, messages, schema)
            last_tokens = tokens
            if ok:
                messages = [
                    {"role": "system", "content": SYSTEM},
                    {"role": "system", "content": "Compressed conversation state:\n" + json.dumps(state, ensure_ascii=False)},
                ]
                print(json.dumps(state, ensure_ascii=False, indent=2))
            else:
                print(f"compression_failed: {error}")
            continue
        messages.append({"role": "user", "content": text})
        answer, last_tokens = chat(client, messages)
        messages.append({"role": "assistant", "content": answer})
        print(f"assistant> {answer}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    client = OpenAI()
    if args.interactive:
        interactive(client)
        return
    a_tokens, a_probes, _ = run_script(client, False)
    b_tokens, b_probes, state = run_script(client, True)
    print_run("A — never compressed", a_tokens, a_probes, None)
    print_run("B — compressed", b_tokens, b_probes, state)


if __name__ == "__main__":
    main()
