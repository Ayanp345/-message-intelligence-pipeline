
The **raw dataset (`messages.csv`) is intentionally not included** in this
repository, per the assignment rules. `pipeline.py` takes its path as a
command-line argument so anyone with the original file can regenerate all
outputs locally.

## Part 1 — Classification

`classifier.py` runs an **ordered rule cascade** (first match wins), most
specific rule first:

1. `promotional` — message contains a discount-code / marketing phrase
   (`Use code SAVE...`, `You may like our new student plan`).
2. `sensitive_information` — reuses the Part 3 detector; if any sensitive
   pattern fires, the message is sensitive regardless of anything else
   in it.
3. `meeting_or_event` — matches one of the 5 known scheduling templates
   (`Calendar update: ...`, `Reminder: ... happens on ...`, `Please join
   the ... on ...`, `... is scheduled for ...`, `Are you available for
   the ... at ... on ...?`).
4. `action_required` — matches one of the known request/reminder/deadline
   templates (`Can you ... before DATE?`, `Please ... by DATE`,
   `Don't forget to ...; deadline is DATE`, etc.).
5. `personal_information` — starts with a self-report marker (`For my
   profile,`, `Personal note:`, `Remember that`, `Just so you know,`)
   describing a preference, not a secret.
6. `general_information` — fallback: a plain status statement (nothing
   asked, nothing scheduled, no secret, no preference marker).

Every record includes a `reason` string and a `confidence` score. Confidence
is higher for structural template matches (0.88–0.97) and lower for the
catch-all fallback (0.7), reflecting that "no rule matched" is a weaker
signal than "an explicit template matched."

## Part 2 — Task / Event extraction

`extractor.py` first strips the envelope prefix, then tries the 5 event
regexes and ~15 task regexes built directly from the templates found
during inspection. Each regex captures the concrete fields (title, date,
time, location/person) with **named capture groups** — nothing is inferred
outside of what the regex actually captured.

Deliberately unresolved cases (do not invent missing data, per the brief):
- `"Could you send it soon?"` → task, `deadline: null` (no date given at
  all).
- `"If possible, review the file before the meeting."` → task,
  `deadline: null` ("before the meeting" is relative, not a date).
- `"The report may be needed tomorrow."` → task, `deadline: null`
  (`"tomorrow"` is relative to an unknown reference point once read out
  of chronological context; the pipeline does not resolve relative dates).
- `"Let us meet sometime next week."` / `"The review could be Friday
  afternoon."` → event, `date: null`, `time: null`.

**Priority** for tasks is derived from `(deadline − message timestamp)`
in days: ≤3 days → `high`, 4–7 days → `medium`, >7 days → `low`, no
resolvable deadline → `unresolved`. For events, priority is a light
keyword heuristic (interview/review/briefing → `high`; casual personal
events like a family dinner → `low`; everything else → `medium`) —
this is the one place I made a judgment call rather than reading it
directly off the text, and I say so explicitly in the video.

## Part 3 — Sensitive information detection & masking

`sensitive_detector.py` has one rule per sensitivity type found in the
data: `password`, `one_time_password`, `bank_card_number`,
`bank_account_number`, `auth_token`, `account_recovery_code`,
`personal_identification_number`, `private_address`,
`private_phone_number`, `health_information`. Each rule is a regex with a
single capture group around **only the sensitive span** (not the whole
sentence), a `risk` level (`high` for credentials/financial data,
`medium` for address/phone/health), and a `recommended_action`
(`do_not_store` for credentials, `ask_for_confirmation` for
address/phone/health).

Masking replaces the captured span with asterisks and is applied **before
anything is written to disk** — `sensitive_findings.json` and
`display_messages.json` (used by the demo UI) never contain a raw secret
value. The detector and masker run in the same module so there's no path
where a match is found but the mask step is skipped.

Sensitive detection (Part 3) runs on **every** message independently of
its Part 1 category — a message classified `personal_information` can
still trigger a sensitive finding (e.g. a home address), and the two
outputs are cross-referenced in `mandatory_ids_report.json`.

## Assumptions

- The CSV is already in chronological order (verified: timestamps are
  monotonically increasing); the pipeline preserves file order rather
  than re-sorting.
- "Deadline" and "date" are the same concept for tasks vs. events
  respectively; both are ISO `YYYY-MM-DD` strings taken verbatim from the
  message, never reformatted or guessed.
- A `person` field is only populated when a name from the small fixed
  cast of senders (`Meera, Ishaan, Kabir, Aarav, Ananya, Neha, Tara,
  Vikram, Rohan, Maya`) appears explicitly in the message text — the
  sender of the message is not automatically treated as the "person
  involved," since in this dataset the sender is usually the requester,
  not the assignee.
- Where the same underlying fact template appears with and without an
  envelope prefix (e.g. `"FYI: My account recovery code is..."` vs
  `"My account recovery code is..."`), both are treated identically.

## Limitations & possible improvements

- **Rule coverage is tied to the templates observed in this dataset.**
  A message phrased differently from all 126 templates (e.g. a typo-laden
  or free-form real email) would fall through to `general_information`
  with low confidence rather than being correctly classified — this is
  the main gap between this prototype and a production system.
- **Relative dates are never resolved** ("tomorrow", "next week", "Friday
  afternoon") by design, per the "do not invent missing information"
  rule — a production version could resolve these against the message
  timestamp *if* the assignment allowed inferring dates, with a
  clearly-lower confidence score.
- **Event priority is a heuristic**, not extracted from the text, and is
  the weakest-justified field in the whole system.
- **No fuzzy/typo-tolerant matching** — regex is exact. A future version
  could add a local embedding-similarity fallback (e.g.
  `sentence-transformers` run fully offline) for messages that don't
  match a known template, keeping the "no external API" guarantee.
- The sensitive-detection rule list is exhaustive for *this* dataset but
  not general-purpose PII detection (e.g. it wouldn't catch a SSN written
  in a different format, or a password embedded mid-sentence without the
  word "password").

## AI-tool usage declaration

This solution was built with Claude (Anthropic) as a coding assistant,
inside a sandboxed environment with no access to the original dataset
beyond what was provided, and no calls to any external LLM/API from the
pipeline code itself. Claude was used to write the regex rules and
Flask/HTML demo after I supplied the extracted message templates; every
rule was verified against the actual dataset output (see the test/spot-
check commands in `notes/verification.md` if included) before being
accepted. No message content was sent to any third-party AI service — all
processing shown in the demo runs 100% locally against the CSV.

## Running it

```bash
pip install -r requirements.txt

# 1. Regenerate all outputs from the raw CSV
python3 src/pipeline.py /path/to/messages.csv /path/to/mandatory_demo_ids.csv output/

# 2. Run the demo UI locally
cd app && python3 app.py
# -> http://localhost:5000
