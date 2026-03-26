# Nightingale

Open-source clinical documentation assistant that runs entirely on-device. No patient data ever leaves the machine.

## What it does

Nurses and providers type quick clinical notes in any format — shorthand, fragments, abbreviations. Nightingale transforms them into properly structured medical documentation ready to paste into the EHR.

**Input** (10 seconds):
```
bed 4 johnson 78F post-op day 2 hip. vitals 128/82 hr 76
temp 98.4. wound clean dry intact. ambulated to bathroom
assist x1. pain 4/10 on scheduled tylenol. oriented x4
lungs clear bilat
```

**Output** (formatted nursing assessment):
```
PATIENT: Johnson, 78F | Bed 4
POST-OP DAY: 2 — Total Hip Arthroplasty

VITAL SIGNS:
  BP 128/82 | HR 76 | Temp 98.4°F | Within normal limits

NEUROLOGICAL: Alert & oriented x4
RESPIRATORY: Lungs clear bilateral
SURGICAL SITE: Wound clean, dry, intact. No signs of infection.
MOBILITY: Ambulated to bathroom with assist x1. Tolerating activity.
PAIN: 4/10, managed with scheduled acetaminophen. Adequate control.

PLAN: Continue current care plan. Monitor surgical site.
Progress mobility as tolerated.
```

Copy. Paste into Epic. Done in 30 seconds instead of 10 minutes.

## Why local matters

Nightingale runs a 35-122 billion parameter AI model directly on a Mac. Nothing is sent to any server, cloud, or API.

- No internet connection required
- No cloud processing of patient data
- No third-party data agreements needed
- No per-seat licensing fees
- Full audit trail stays on the device

The model processes everything locally using [Kandiga](https://github.com/kantheon/kandiga), an inference engine that runs frontier MoE models in 2-4GB of RAM on Apple Silicon.

## Install

```bash
pip install nightingale-ai
```

This installs Nightingale and Kandiga together. First run downloads the AI model (~20GB one-time).

**Requirements:** Mac with Apple Silicon (M1/M2/M3/M4), 16GB RAM recommended, Python 3.10+

## Usage

```bash
nightingale
```

Opens a web interface at `http://localhost:3000`. Click **Start Shift**, type notes, get formatted documentation.

### Shift workflow

1. **Start shift** — loads the model and begins tracking patients
2. **Document patients** — type quick notes, get formatted assessments, SOAP notes, or SBAR handoffs
3. **Ongoing updates** — model remembers every patient from the shift. "Update bed 4, potassium came back 3.2" and it has full context
4. **Save handoff** — saves the entire shift state to disk
5. **Load handoff** — incoming nurse loads the saved shift and picks up with full context. No verbal report needed.

### Documentation formats

- **Nursing Assessment** — structured by body system
- **SOAP Note** — Subjective, Objective, Assessment, Plan
- **SBAR Handoff** — Situation, Background, Assessment, Recommendation

## How it works

Nightingale is a focused layer on top of Kandiga:

```
Nurse types quick notes
        |
        v
  [Nightingale]
  Clinical prompts + templates + shift management
        |
        v
  [Kandiga Engine]
  35-122B model running locally in 2-4GB RAM
  Persistent KV cache (remembers full shift)
  Custom Metal GPU kernels on Apple Silicon
        |
        v
  Formatted clinical documentation
  (copy into EHR)
```

### Persistent shift memory

Most AI tools forget everything between messages. Nightingale maintains context across the entire shift using persistent KV cache:

- First patient assessment: ~8 seconds
- Every update after that: ~3 seconds
- Works the same whether it's patient 1 or patient 15
- Save to disk at end of shift, load instantly on next shift

### Shift handoff

End of shift, one click saves everything — the model's full context, patient list, and documentation history. The incoming nurse loads the handoff file and has complete continuity without a 30-minute verbal report.

## Deployment

**Single workstation:**
One Mac at the nursing station runs Nightingale. Nurse opens it in the browser.

**Floor deployment:**
One Mac Mini in the supply room serves Nightingale over the hospital's local network. Every workstation on the floor accesses it. Still fully local — nothing leaves the building.

```bash
nightingale --port 3000
# Access from any machine on the local network
```

## Privacy and compliance

- All processing happens on-device
- No data is transmitted to any external service
- No internet connection is required after initial model download
- All shift data is stored locally and can be deleted at any time
- Open source — every line of code is auditable

## Roadmap

- [ ] Voice input (dictation to structured notes)
- [ ] Drug interaction database (local, no API)
- [ ] Lab value trending and critical value alerts
- [ ] Direct EHR integration (FHIR/HL7)
- [ ] Multi-language clinical documentation
- [ ] Custom templates per facility

## License

MIT — Built by [Kantheon](https://kantheon.com)
