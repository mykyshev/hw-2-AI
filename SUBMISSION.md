# HW2 submission

**Name:** Renat Mykysh  
**Student ID:**  
**Group:**  
**Repository:**

## Sublab Easy — one task, four roles

### Decisions per role

| Enquiry | policy_officer| front_desk   | auditor      | bilingual_clerk |
|---      |---            |---           |---           |              ---|
| E-01    | granted ✓    | granted ✓   | more_info ✗ | granted ✓ |
| E-02    | more_info ✓  | more_info ✓ | more_info ✓ | more_info ✓ |
| E-03    | refused ✓    | more_info ✗ | refused ✓   | refused ✓ |
| E-04    | refused ✓    | more_info ✗ | refused ✓   | refused ✓ |
| E-05    | granted ✓    | granted ✓   | more_info ✗ | granted ✓ |
| E-06    | granted ✓    | granted ✓   | more_info ✗ | granted ✓ |
| E-07    | granted ✓    | granted ✓   | more_info ✗ | granted ✓ |
| E-08    | not_found ✓  | not_found ✓ | not_found ✓ | not_found ✓ |
| E-09    | refused ✓    | more_info ✗ | refused ✓   | refused ✓ |
| E-10    | more_info ✓  | more_info ✓ | more_info ✓ | more_info ✓ |
| **agrees with `expected`** | **10/10** | **7/10** | **6/10** | **10/10** |
| **parsed** | **10/10** | **10/10** | **10/10** | **10/10** |
| **schema-valid** | **10/10** | **10/10** | **10/10** | **10/10** |

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | none | none |
| `decision` | E-01, E-03, E-04, E-05, E-06, E-07, E-09 | auditor, front_desk |
| `amount` | E-01, E-05, E-06, E-07 | auditor |
| `missing_documents` | none | none |

### Raw replies

One enquiry where a role changed the decision away from the policy officer:

```json
{"applicant_id":"A-201","found":true,"decision":"more_info","amount":0,"missing_documents":[],"reason":"The authoritative record shows GPA 3.4, income band 1, and both required documents (transcript and id_card), satisfying the Need-based study grant 2026 rule. Second-reader verification is required before granting."}
```

E-07 from the bilingual clerk:

```json
{"applicant_id":"A-201","found":true,"decision":"granted","amount":250000,"missing_documents":[],"reason":"Сіз грант талаптарына сай келесіз: GPA көрсеткіші 3.4, табыс санаты 1 және транскрипт пен жеке куәлік құжаттары тіркелген. Грант мөлшері — 250 000 теңге."}
```

### Written answers

**1. Which fields are role-sensitive and which are not?**

`decision` was the most role-sensitive field. It moved on E-01, E-03, E-04, E-05, E-06, E-07 and E-09 under the auditor or front_desk roles. `amount` also moved on E-01, E-05, E-06 and E-07 under the auditor because a grant became `more_info`, so the amount was no longer awarded. `found` and `missing_documents` never moved in my run. The bilingual clerk matched the policy officer on all checked structured fields and changed only the language of `reason` when needed, as visible in E-07.

**2. Which enquiries are most sensitive to the role, and why those?**

E-03 and E-04 test cases where the policy produces a refusal, so they are sensitive to `front_desk`, whose role says not to turn an applicant away and to return `more_info` instead. E-07 tests language behavior: the structured decision stayed `granted`, while the bilingual clerk wrote the reason in Kazakh. E-10 tests whether a claim made by the applicant can override the authoritative record. It cannot: the record wins, so the result stayed `more_info`. More generally, the granted and refused cases were the most sensitive because the auditor can turn grants into second-reader `more_info`, while the front desk can turn refusals into `more_info`.

**3. Where does discretion belong — the role paragraph, or code that reads `decision` afterwards?**

The role paragraph is useful for defining conversational behavior, but expensive or important policy discretion should not exist only in the prompt. A downstream program that receives a JSON record can see fields such as `decision` and `amount`, but those fields do not by themselves prove which role produced them or why that role changed them. If different roles are allowed to change operational outcomes, I would make that policy explicit in code or include and validate a role/provenance field before acting on the result.

**4. Is a role a boundary?**

No. In Week 2 terms, the role paragraph is still tokens in the model context. It influences the continuation produced by the model, but it is not a security or correctness boundary. If a wrong `decision` were expensive, I would validate the JSON in code, check the decision again against the authoritative records and policy, reject impossible state transitions, and require deterministic checks or human approval before an action such as paying a grant.

---

## Sublab Medium — memory you choose

### Tokens per call

`chat_script.json` contains 12 conversation entries, but one entry is the `<compress>` command rather than an applicant message. It is skipped in the uncompressed run and triggers compression in the compressed run, so there are 11 normal model calls in each comparison run.

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---:|---:|
| 1 | 64 | 64 |
| 2 | 118 | 127 |
| 3 | 197 | 207 |
| 4 | 284 | 296 |
| 5 | 370 | 373 |
| 6 | 469 | 466 |
| 7 | 545 | 560 |
| 8 | 640 | 649 |
| 9 | 722 | 727 |
| 10 | 807 | 335 |
| 11 | 941 | 439 |
| 12 | N/A — `<compress>` is a command | N/A — `<compress>` is a command |
| **peak** | **941** | **727** |
| **total for the run** | **5157** | **4243** |

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | Yes | Daniyar Qoshan, A-202 | Yes | Daniyar Qoshan, A-202 |
| Q-2 missing document | turn 5 | Yes | ID card | Yes | ID card copy |
| Q-3 band and amount | turns 3–4 | No | Remembered income band 2, but did not return 150000 | No | Remembered income band 2, but did not return 150000 |
| Q-4 the constraint | turn 6 | Yes | Thursday | Yes | Thursday |
| Q-5 the open question | turn 7 | Yes | Asked whether a scanned employer letter counts or the original is required | Yes | Asked whether a scanned employer letter counts or the original is required |
| **retrieved** | | **4/5** | | **4/5** | |

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "Study grant eligibility and application documents",
  "facts": [
    "The applicant's name is Daniyar Qoshan.",
    "The applicant sent their transcript last week.",
    "The applicant's family certificate places them in income band 2.",
    "The applicant could not upload their ID card because their home scanner broke.",
    "The applicant's sister, Aruzhan, applied last year and has a file with the office."
  ],
  "decisions": [
    "The applicant's grant eligibility has not been confirmed.",
    "The potential grant amount has not been established.",
    "The applicant's application is not confirmed complete because the ID card has not been uploaded.",
    "A same-day decision on Thursday is not guaranteed."
  ],
  "constraints": [
    "The applicant can come to the office only on Thursdays because they have lab all other days.",
    "The acceptability of a scanned employer letter depends on the program's document rules.",
    "The application must undergo document verification and eligibility assessment."
  ],
  "open_questions": [
    "Does the applicant qualify for the study grant?",
    "How much would the grant amount be if approved?",
    "Does a scanned letter from the employer count, or is the original required?",
    "If the applicant brings the ID card on Thursday, will the decision be made the same day?"
  ],
  "language": "English"
}
```

### Written answers

**1. What did compression buy?**

Without compression, the peak prompt size was 941 tokens and the total was 5157. 
With compression, the peak fell to 727 and the total to 4243.
That is 214 fewer peak tokens and 914 fewer tokens over the run.
Both modes retrieved 4/5 probes, so in this run compression reduced
context cost without reducing the measured probe score. Q-3 failed in both modes: 
the model remembered income band 2 but did not retrieve the expected amount 150000 from turns 3–4.
Because the same probe failed without compression, this failure cannot be attributed only to the compressed state.

**2. Why must the state be structured rather than a paragraph?**

A structured object gives the program named fields with known types and a schema that can be validated. The program can reliably distinguish identity, facts, decisions, constraints and open questions instead of trying to recover them later from free prose. A paragraph may sound correct while silently omitting or blending facts. With structured state, malformed or incomplete output can be detected before it replaces the original conversation.

**3. What is missing from your state that you would add?**

I would add a field for important numeric policy results or referenced values, for example `known_amounts` or `policy_values`. Q-3 shows why: the state retained income band 2 and the open question about the amount, but not the expected numeric amount 150000. To keep the state small, I would drop lower-priority background facts such as the sister Aruzhan having applied last year, because that fact was not needed for the five probes or the current application decision.

**4. When is compression the wrong choice?**

Compression is the wrong choice when exact wording, chronology, evidence or legally important details must be preserved, for example a dispute where the exact promises and dates in a conversation may later be audited. A summary can omit a qualifier or merge two statements, and the original detail cannot be reconstructed after the history is discarded. My program would notice if the state failed JSON parsing or schema validation, but it would not necessarily notice a fluent, schema-valid summary that omitted a fact. That is a semantic-loss problem rather than a syntax-validation problem.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 | Yes | Yes | none | non-published paper/output |
| story-02 | Yes | Yes | graduation_year, gpa_4_scale, gpa_original, published_peer_reviewed_outputs | no/contradicted GPA, non-published paper/output, contradiction |
| story-03 | Yes | Yes | none | GPA on another scale, non-published paper/output |
| story-04 | Yes | Yes | none | non-published paper/output |
| story-05 | Yes | Yes | none | non-published paper/output |
| story-06 | Yes | Yes | graduation_year, gpa_4_scale | no/contradicted GPA, GPA on another scale, non-published paper/output, contradiction |

### story-06 extraction

```json
{
  "candidate_id": "story-06",
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_4_scale": null,
  "gpa_original": "3.2 or 3.5; scale not stated",
  "languages": [
    "Kazakh",
    "Russian",
    "English"
  ],
  "published_peer_reviewed_outputs": 1,
  "other_research_outputs": [
    "One poster at a local event"
  ],
  "relevant_experience_months": 40,
  "uncountable_experience": [],
  "ambiguities": [
    "Graduation year contradicts itself: the candidate says they graduated in 2024 and also says they are a final-year student graduating in 2026.",
    "GPA contradicts itself: the candidate states 3.2 and later says it may have been 3.5; the GPA scale is not stated."
  ],
  "evidence": {
    "full_name": "# Nurzhan Abilov",
    "degree": "I graduated in 2024 with a BSc in Statistics.",
    "graduation_year": "I graduated in 2024 ... I am currently a final-year student graduating in 2026",
    "gpa": "My GPA was 3.2. Actually I should double-check that, I think it was 3.5",
    "languages": "Languages: Kazakh, Russian, English.",
    "publications": "one paper published, in a peer-reviewed proceedings, on survey weighting",
    "experience": "I have been at an insurance analytics team since February 2023, which is about forty months."
  }
}
```

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---:|---:|---:|---:|
| story-01 | 5 | 5 | 2 | **4.40** |
| story-02 | 1 | 0 | 5 | **1.50** |
| story-03 | 4 | 2.5 | 3 | **3.35** |
| story-04 | 4 | 3 | 5 | **3.90** |
| story-05 | 5 | 2.5 | 1.25 | **3.50** |
| story-06 | 1 | 2 | 5 | **2.10** |

**Winner, computed by my code:** `story-01` — Aziza Bekova, weighted total **4.40**.

**The model's prose answer, asked separately ("who should win?"):**

> **Aziza Bekova should receive the scholarship.** She has a strong, clearly documented academic record (GPA 3.8/4.0), two published peer-reviewed research outputs—the highest research record among the candidates—and eight months of directly relevant experience. Although some candidates have longer work experience, none combines Aziza’s top academic and research performance as convincingly under the stated weighting.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?**

The most important rule was that contradictions must not be resolved, guessed or averaged: the affected field becomes `null` and the conflict is recorded in `ambiguities`. Story-06 forced this rule because it says both that the candidate graduated in 2024 and is a final-year student graduating in 2026, and it gives GPA as both 3.2 and possibly 3.5. Without the rule, the model could arbitrarily choose one value and make the record look more certain than the source actually is. The publication-status rule was also necessary so submitted, under-review, in-preparation and in-press work was not counted as published.

**2. Where did the model guess, and where did your code have to decide?**

The model still had to make judgement calls when converting evidence into rubric scores. For example, story-05 received an experience score of 1.25, which is a model judgement within the 0–5 rubric rather than a directly stated number in the story. My code then had to make the deterministic ranking decision: it applied `0.5 * academic + 0.3 * research + 0.2 * experience`, rounded the totals, compared all six candidates and selected story-01 with 4.40. The model did not get to assert that computed total in the scoring call.

**3. Did your prose ranking and your computed ranking agree?**

Yes. Both selected story-01, Aziza Bekova. I trust the computed ranking more because I can inspect the three input scores, the rubric weights and the exact formula that produced 4.40. Agreement with the prose answer is useful, but before trusting prose alone I would need evidence that it consistently applies the same rubric, weights, publication-counting rules and contradiction handling across repeated runs. A fluent explanation is not proof that the calculation was performed correctly.

**4. The rubric has no anchor for a contradicted field.**

For story-06 I kept `gpa_4_scale` as `null` and recorded both conflicting GPA statements in `ambiguities` instead of choosing 3.2, choosing 3.5 or averaging them. In my scoring run the academic score was 1, showing that the model still had to interpret an underspecified case. I think the rubric should explicitly define contradicted evidence, for example: if a required numeric field has unresolved contradictory values, treat that field as unavailable for scoring and use a stated fallback score, or send the candidate for manual review. That would remove hidden model discretion.

**5. How close were your top two candidates?**

The top two were story-01 at 4.40 and story-04 at 3.90, so the gap was **0.50**. This is much larger than the 0.05 threshold in the question, so I would not describe this run as a near tie. If the gap had been within 0.05, I would tell the committee that the ranking is sensitive to extraction/scoring uncertainty and should not be treated as a confident automatic decision. I would strengthen the extraction with more explicit evidence fields, verify dates and publication status, repeat or independently review the extraction, and require a human check before choosing the winner.

---

## Reflection

This homework showed me that reliable model output depends on more than writing a good prompt. Next time I build a system around an LLM, I will define a schema first, validate every response, keep authoritative rules and expensive decisions in deterministic code where possible, and treat conversation memory as selected state rather than unlimited history. I will also preserve evidence and ambiguity instead of letting the model silently turn uncertain text into certain-looking fields.
