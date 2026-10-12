import json
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import validate
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-5.6-luna"

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_id": {"type": "string"},
        "full_name": {"type": ["string", "null"]},
        "degree": {"type": ["string", "null"]},
        "graduation_year": {"type": ["integer", "null"]},
        "gpa_4_scale": {"type": ["number", "null"], "minimum": 0, "maximum": 4},
        "gpa_original": {"type": ["string", "null"]},
        "languages": {"type": ["array", "null"], "items": {"type": "string"}},
        "published_peer_reviewed_outputs": {"type": ["integer", "null"], "minimum": 0},
        "other_research_outputs": {"type": "array", "items": {"type": "string"}},
        "relevant_experience_months": {"type": ["integer", "null"], "minimum": 0},
        "uncountable_experience": {"type": "array", "items": {"type": "string"}},
        "ambiguities": {"type": "array", "items": {"type": "string"}},
        "evidence": {
            "type": "object",
            "properties": {
                "full_name": {"type": ["string", "null"]},
                "degree": {"type": ["string", "null"]},
                "graduation_year": {"type": ["string", "null"]},
                "gpa": {"type": ["string", "null"]},
                "languages": {"type": ["string", "null"]},
                "publications": {"type": ["string", "null"]},
                "experience": {"type": ["string", "null"]},
            },
            "required": ["full_name", "degree", "graduation_year", "gpa", "languages", "publications", "experience"],
            "additionalProperties": False,
        },
    },
    "required": ["candidate_id", "full_name", "degree", "graduation_year", "gpa_4_scale", "gpa_original", "languages", "published_peer_reviewed_outputs", "other_research_outputs", "relevant_experience_months", "uncountable_experience", "ambiguities", "evidence"],
    "additionalProperties": False,
}

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "academic": {"type": "number", "minimum": 0, "maximum": 5},
        "research": {"type": "number", "minimum": 0, "maximum": 5},
        "experience": {"type": "number", "minimum": 0, "maximum": 5},
    },
    "required": ["academic", "research", "experience"],
    "additionalProperties": False,
}


def load_json(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def json_call(client, system, user):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def extract(client, candidate_id, story):
    system = '''Extract a structured scholarship CV from the story. Return exactly one JSON object matching the requested schema and no prose outside JSON.
Rules:
1. A fact the story does not state is null. Never estimate or infer a missing fact.
2. Convert a stated GPA from another scale proportionally to a 4.0 scale and record the original GPA and scale in gpa_original. If no GPA is stated, gpa_4_scale is null.
3. A peer-reviewed output counts as published only if the story says published or accepted. Submitted, under review, in preparation, planned, and in press do not count as published. Record those separately in other_research_outputs.
4. Contradictions are never resolved, averaged, or guessed. Any contradicted scalar field is null and the contradiction is recorded in ambiguities.
5. Count relevant experience in months, not jobs. Overlapping periods count once. A period with no dates is not countable and must be recorded in uncountable_experience.
6. Evidence values must be short exact quotes from the story supporting each filled field. Use null evidence when the field has no usable evidence.
7. If degree status or graduation year contradicts itself, set the contradicted field to null and record the contradiction.
Schema:
''' + json.dumps(EXTRACTION_SCHEMA, ensure_ascii=False)
    raw = json_call(client, system, f"Candidate id: {candidate_id}\n\nStory:\n{story}")
    data = json.loads(raw)
    validate(data, EXTRACTION_SCHEMA)
    return raw, data


def score(client, candidate, rubric):
    system = '''Score one scholarship candidate using exactly the supplied rubric and counting rules. Return exactly one JSON object with only academic, research, and experience scores from 0 to 5. Do not compute a weighted total, do not rank candidates, and do not add explanations. Use the extracted fields as authoritative. For a contradicted field represented as null, do not invent a value; score only what the rubric and uncontradicted extracted evidence support.
Rubric:
''' + json.dumps(rubric, ensure_ascii=False)
    raw = json_call(client, system, json.dumps(candidate, ensure_ascii=False))
    data = json.loads(raw)
    validate(data, SCORE_SCHEMA)
    return data


def null_fields(data):
    return [key for key, value in data.items() if value is None]


def trap_labels(data):
    labels = []
    if data.get("gpa_4_scale") is None:
        labels.append("no/contradicted GPA")
    original = data.get("gpa_original") or ""
    if original and "4.0" not in original and "/4" not in original:
        labels.append("GPA on another scale")
    if data.get("other_research_outputs"):
        labels.append("non-published paper/output")
    if data.get("ambiguities"):
        labels.append("contradiction")
    return labels


def main():
    load_dotenv(ROOT / ".env")
    client = OpenAI()
    rubric = load_json("candidate_rubric.json")
    extracted = {}
    raw_extractions = {}

    print("=== EXTRACTION ===")
    print("story\tparsed\tvalid\tnull_fields\ttraps")
    for path in sorted((ROOT / "data" / "candidates").glob("story-*.md")):
        candidate_id = path.stem
        story = path.read_text(encoding="utf-8")
        parsed = False
        valid = False
        data = None
        raw = ""
        try:
            raw, data = extract(client, candidate_id, story)
            parsed = True
            valid = True
            extracted[candidate_id] = data
            raw_extractions[candidate_id] = raw
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            if raw:
                try:
                    data = json.loads(raw)
                    parsed = True
                except Exception:
                    pass
            print(f"{candidate_id}\t{parsed}\t{valid}\tERROR\t{exc}")
            continue
        print(f'{candidate_id}\t{parsed}\t{valid}\t{", ".join(null_fields(data)) or "none"}\t{", ".join(trap_labels(data)) or "none"}')

    print("\n=== STORY-06 EXTRACTION ===")
    if "story-06" in extracted:
        print(json.dumps(extracted["story-06"], ensure_ascii=False, indent=2))

    scores = {}
    print("\n=== SCORES ===")
    print("candidate\tacademic\tresearch\texperience\tweighted_total")
    for candidate_id, candidate in extracted.items():
        values = score(client, candidate, rubric)
        total = round(0.5 * values["academic"] + 0.3 * values["research"] + 0.2 * values["experience"], 2)
        scores[candidate_id] = {**values, "weighted_total": total}
        print(f'{candidate_id}\t{values["academic"]}\t{values["research"]}\t{values["experience"]}\t{total}')

    ranking = sorted(scores.items(), key=lambda item: item[1]["weighted_total"], reverse=True)
    winner = ranking[0][0] if ranking else None
    print(f"\nWINNER_COMPUTED_BY_CODE: {winner}")
    if len(ranking) >= 2:
        print(f"TOP_TWO_GAP: {round(ranking[0][1]['weighted_total'] - ranking[1][1]['weighted_total'], 2)}")

    prose_response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are advising a scholarship committee. Using the supplied extracted candidate records and rubric, answer in prose which candidate should win and briefly explain why."},
            {"role": "user", "content": json.dumps({"rubric": rubric, "candidates": extracted}, ensure_ascii=False)},
        ],
    )
    print("\n=== MODEL PROSE ANSWER ===")
    print(prose_response.choices[0].message.content)


if __name__ == "__main__":
    main()
