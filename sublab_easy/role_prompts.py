import json
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import validate
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-5.6-luna"

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "applicant_id": {"type": ["string", "null"]},
        "found": {"type": "boolean"},
        "decision": {"type": "string", "enum": ["granted", "refused", "more_info", "not_found"]},
        "amount": {"type": "integer", "minimum": 0},
        "missing_documents": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["applicant_id", "found", "decision", "amount", "missing_documents", "reason"],
    "additionalProperties": False,
}

ROLES = {
    "policy_officer": "You are a policy officer. Apply the grant rule exactly as written. Grant what the rule allows, refuse what it refuses, ask for missing documents, soften nothing, and never treat a claim in the enquiry as evidence. The supplied records are authoritative.",
    "front_desk": "You are a front-desk grant clerk. Never turn an applicant away with a refusal. If the policy officer would refuse an applicant who is found in the records, return more_info instead and explain what condition would have to change for the applicant to qualify. Missing documents also produce more_info. A person not found in the records remains not_found. Never treat a claim in the enquiry as evidence.",
    "auditor": "You are an auditor. Never grant on a first reading. Report what the authoritative record shows. Any case that would otherwise be granted must be marked more_info for second-reader verification, and the reason must name the rule or document relied on. Preserve genuine refusals, missing-document cases, and not_found results according to the record. Never treat a claim in the enquiry as evidence.",
    "bilingual_clerk": "You are a bilingual grant clerk. Decide exactly as the policy officer would under the authoritative record and policy. The only role-specific change is that reason must be written in the language of the enquiry. Never treat a claim in the enquiry as evidence.",
}

FIELDS = ["found", "decision", "amount", "missing_documents"]


def load_json(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def call_model(client, role, enquiry, records, policy):
    system = f'''{ROLES[role]}
Return exactly one JSON object matching this contract:
{{
  "applicant_id": string or null,
  "found": boolean,
  "decision": one of "granted", "refused", "more_info", "not_found",
  "amount": non-negative integer,
  "missing_documents": array of strings,
  "reason": string
}}
Use amount 0 unless the decision is granted. If the applicant is not found, use found=false, decision="not_found", amount=0, and an empty missing_documents array.
Policy:
{json.dumps(policy, ensure_ascii=False)}
Authoritative records:
{json.dumps(records, ensure_ascii=False)}'''
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": enquiry["text"]},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def main():
    load_dotenv(ROOT / ".env")
    client = OpenAI()
    records = load_json("records.json")
    policy = load_json("policy.json")
    enquiries = load_json("enquiries.json")
    results = {role: {} for role in ROLES}

    for role in ROLES:
        print(f"\n=== {role} ===")
        print("enquiry\tdecision\tparsed\tvalid\tagrees")
        for enquiry in enquiries:
            raw = call_model(client, role, enquiry, records, policy)
            parsed = False
            valid = False
            agrees = False
            data = None
            try:
                data = json.loads(raw)
                parsed = True
                validate(data, ANSWER_SCHEMA)
                valid = True
                agrees = all(data.get(field) == enquiry["expected"].get(field) for field in FIELDS)
            except Exception:
                pass
            results[role][enquiry["id"]] = {"raw": raw, "data": data, "parsed": parsed, "valid": valid, "agrees": agrees}
            decision = data.get("decision") if isinstance(data, dict) else "PARSE_ERROR"
            print(f'{enquiry["id"]}\t{decision}\t{parsed}\t{valid}\t{agrees}')
        print(f'agrees={sum(x["agrees"] for x in results[role].values())}/10 parsed={sum(x["parsed"] for x in results[role].values())}/10 valid={sum(x["valid"] for x in results[role].values())}/10')

    print("\n=== FIELD MOVEMENT FROM POLICY OFFICER ===")
    print("field\tenquiries\troles")
    for field in FIELDS:
        moved_enquiries = []
        moved_roles = []
        for enquiry in enquiries:
            eid = enquiry["id"]
            base = results["policy_officer"][eid]["data"]
            if not isinstance(base, dict):
                continue
            roles_here = []
            for role in ROLES:
                if role == "policy_officer":
                    continue
                current = results[role][eid]["data"]
                if isinstance(current, dict) and current.get(field) != base.get(field):
                    roles_here.append(role)
            if roles_here:
                moved_enquiries.append(eid)
                moved_roles.extend(roles_here)
        print(f'{field}\t{", ".join(moved_enquiries) or "none"}\t{", ".join(sorted(set(moved_roles))) or "none"}')

    print("\n=== RAW ROLE-CHANGED DECISION ===")
    shown = False
    for enquiry in enquiries:
        eid = enquiry["id"]
        base = results["policy_officer"][eid]["data"]
        for role in ["front_desk", "auditor"]:
            current = results[role][eid]["data"]
            if isinstance(base, dict) and isinstance(current, dict) and current.get("decision") != base.get("decision"):
                print(f"{eid} / {role}")
                print(results[role][eid]["raw"])
                shown = True
                break
        if shown:
            break

    print("\n=== E-07 BILINGUAL CLERK ===")
    print(results["bilingual_clerk"]["E-07"]["raw"])


if __name__ == "__main__":
    main()
