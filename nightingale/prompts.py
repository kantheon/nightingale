"""Clinical documentation prompts and templates."""

SYSTEM_PROMPT = """You are a clinical documentation assistant for nurses and healthcare providers. Your role is to take quick, informal clinical notes and transform them into properly formatted medical documentation.

Rules:
- Use standard medical terminology and abbreviations
- Organize findings by body system
- Flag any critical or abnormal values
- Never fabricate clinical data — only document what was provided
- If information is missing, leave that section blank rather than assuming
- Use professional clinical language appropriate for medical records
- Include time stamps when provided
- Maintain HIPAA-appropriate language throughout

Output formats you support:
- Nursing Assessment
- SOAP Note
- Shift Handoff Report (SBAR)
- Care Plan Update
- Medication Reconciliation Summary
- Vital Signs Trending Summary"""

FORMAT_NURSING_ASSESSMENT = """Format the following clinical observations as a structured Nursing Assessment.

Use this structure:
PATIENT: [name, age, sex] | [bed/room]
DIAGNOSIS/REASON FOR ADMISSION: [if mentioned]

VITAL SIGNS:
  [BP, HR, RR, Temp, SpO2 — flag abnormals with ⚠]

NEUROLOGICAL:
CARDIOVASCULAR:
RESPIRATORY:
GASTROINTESTINAL:
GENITOURINARY:
SKIN/WOUND:
MUSCULOSKELETAL/MOBILITY:
PAIN:
IV/LINES:
PSYCHOSOCIAL:

PLAN:

Clinical notes:
{input}"""

FORMAT_SOAP = """Format the following clinical observations as a SOAP note.

Use this structure:
PATIENT: [name, age, sex] | [bed/room]
DATE/TIME: [if provided]

S (Subjective):
  Patient-reported symptoms, complaints, and statements.

O (Objective):
  Vital signs, physical exam findings, lab results, observations.

A (Assessment):
  Clinical interpretation of findings. Flag concerns.

P (Plan):
  Interventions, orders, follow-up actions.

Clinical notes:
{input}"""

FORMAT_SBAR = """Format the following clinical information as an SBAR Handoff Report.

Use this structure:
PATIENT: [name, age, sex] | [bed/room]

S (Situation):
  Why is this patient here? Current status in one sentence.

B (Background):
  Relevant medical history, current treatments, recent changes.

A (Assessment):
  Current condition, trending vital signs, concerns.

R (Recommendation):
  What needs to happen next shift. Pending results, scheduled procedures, things to watch.

Clinical notes:
{input}"""

FORMATS = {
    "assessment": FORMAT_NURSING_ASSESSMENT,
    "soap": FORMAT_SOAP,
    "handoff": FORMAT_SBAR,
}
