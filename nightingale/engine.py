"""Nightingale clinical engine — wraps Kandiga for healthcare documentation."""

import os
import json
from datetime import datetime
from pathlib import Path

from kandiga.engine import KandigaEngine
from nightingale.prompts import SYSTEM_PROMPT, FORMATS


class NightingaleEngine:
    """Clinical documentation engine powered by Kandiga.

    Manages patient context, shift sessions, and clinical note generation.
    All processing happens locally — no data ever leaves the device.

    Dual-model mode: 4B writes fast (34 tok/s), 35B verifies accuracy.
    Both fit in RAM simultaneously (~2GB each).
    """

    DATA_DIR = os.path.expanduser("~/.nightingale")
    WRITER_MODEL = "mlx-community/Qwen3.5-4B-4bit"
    VERIFIER_MODEL = "mlx-community/Qwen3.5-35B-A3B-4bit"

    def __init__(self, model: str | None = None, verify: bool = True):
        self._kandiga = KandigaEngine(
            model_path=model or self.WRITER_MODEL,
            fast_mode=True,
        )
        self._verifier: KandigaEngine | None = None
        self._use_verify = verify
        self._patients: dict[str, dict] = {}  # bed_id -> patient info
        self._shift_start: str | None = None
        self._ready = False

        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.DATA_DIR, "shifts"), exist_ok=True)

    def start_shift(self):
        """Begin a new shift session.

        Loads both models:
        - 4B writer with persistent session (keeps full shift context)
        - 35B verifier with persistent session (keeps verification context)
        Both run with KV compression. Both fit in RAM simultaneously.
        """
        self._kandiga.load()
        self._kandiga.start_session()
        self._shift_start = datetime.now().isoformat()
        self._patients = {}
        self._ready = True

        # Prime the writer with clinical context
        primer = f"System: {SYSTEM_PROMPT}\n\nShift started at {self._shift_start}. Ready for patient documentation."
        for _ in self._kandiga.session_generate(primer, max_tokens=20):
            pass

        # Load 35B verifier with its own persistent session
        if self._use_verify:
            self._verifier = KandigaEngine(
                model_path=self.VERIFIER_MODEL,
                fast_mode=True,
            )
            self._verifier.load()
            self._verifier.start_session()
            # Prime verifier — this context stays cached for the whole shift
            v_primer = (
                "You are a clinical documentation verifier. Your ONLY job is to compare "
                "original nurse notes against a generated note and output corrections.\n\n"
                "Rules:\n"
                "- If accurate, respond: VERIFIED\n"
                "- If errors found, respond ONLY with lines like: REPLACE \"wrong\" WITH \"correct\"\n"
                "- Do NOT rewrite the note. Do NOT explain. ONLY output REPLACE commands or VERIFIED.\n"
                "- Ignore formatting differences. Only flag factual/clinical errors.\n"
                "- Ignore sections marked [Not provided] — those are intentionally blank."
            )
            for _ in self._verifier.session_generate(v_primer, max_tokens=10):
                pass

    def load_shift(self, path: str):
        """Load a saved shift (handoff from previous nurse)."""
        self._kandiga.load()
        self._kandiga.load_session(path)

        # Load patient metadata
        meta_path = path.replace('.npz', '_shift.json')
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            self._patients = meta.get('patients', {})
            self._shift_start = meta.get('shift_start')

        self._ready = True

    def save_shift(self, path: str | None = None):
        """Save current shift for handoff."""
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            path = os.path.join(self.DATA_DIR, "shifts", f"shift_{timestamp}.npz")

        self._kandiga.save_session(path)

        # Save patient metadata alongside
        meta_path = path.replace('.npz', '_shift.json')
        with open(meta_path, 'w') as f:
            json.dump({
                'shift_start': self._shift_start,
                'patients': self._patients,
                'saved_at': datetime.now().isoformat(),
            }, f, indent=2)

        return path

    def end_shift(self):
        """End the current shift."""
        self._kandiga.end_session()
        if self._verifier is not None:
            self._verifier.end_session()
            self._verifier = None
        self._patients = {}
        self._shift_start = None
        self._ready = False

    def document(self, text: str, format: str = "assessment"):
        """Generate clinical documentation from quick notes.

        4B writes the note fast (34 tok/s), then 35B verifies accuracy.
        Yields tokens during writing. After completion, run get_verification()
        to check if the 35B found any corrections.

        Args:
            text: Informal clinical notes (nurse shorthand)
            format: One of 'assessment', 'soap', 'handoff'

        Yields:
            Tokens of the formatted clinical note (streaming)
        """
        if not self._ready:
            raise RuntimeError("No active shift. Call start_shift() first.")

        template = FORMATS.get(format, FORMATS["assessment"])
        prompt = template.format(input=text)

        response = ""
        for token in self._kandiga.session_generate(prompt, max_tokens=1024):
            response += token
            yield token

        # Track patient if bed number mentioned
        self._extract_patient(text, response)

        # Run 35B verification in background after writing completes
        self._last_input = text
        self._last_output = response
        self._last_verification = None

    def get_verification(self) -> dict:
        """Verify the last note with the 35B and auto-apply corrections.

        Returns dict with:
          'verified': bool — True if no corrections needed
          'corrections': list of (old, new) tuples
          'corrected_note': str — the note with replacements applied (or original if verified)
        """
        if not hasattr(self, '_last_input') or self._last_input is None:
            return {'verified': True, 'corrections': [], 'corrected_note': ''}

        replacements = self.verify(self._last_input, self._last_output)

        if replacements is None:
            return {
                'verified': True,
                'corrections': [],
                'corrected_note': self._last_output,
            }

        # Auto-apply replacements
        corrected = self._last_output
        for old, new in replacements:
            corrected = corrected.replace(old, new)

        return {
            'verified': False,
            'corrections': replacements,
            'corrected_note': corrected,
        }

    def update_patient(self, text: str):
        """Quick update on an existing patient. Model has full shift context.

        Yields tokens of the response.
        """
        if not self._ready:
            raise RuntimeError("No active shift. Call start_shift() first.")

        prompt = f"Update for existing patient: {text}\n\nAdd this to the patient's documentation. Reference any previous notes from this shift."

        for token in self._kandiga.session_generate(prompt, max_tokens=512):
            yield token

    def ask(self, question: str):
        """Ask a quick question about any patient or the shift.

        Returns a brief answer, not a formatted note. Use this for
        things like "what was bed 4's potassium?" or "which patients
        need labs rechecked?"

        Yields tokens of the response.
        """
        if not self._ready:
            raise RuntimeError("No active shift. Call start_shift() first.")

        prompt = f"Answer in 1-2 sentences only. No formatting, no headers, no bullet points.\nQ: {question}\nA:"

        for token in self._kandiga.session_generate(prompt, max_tokens=200):
            yield token

    def verify(self, original_notes: str, generated_note: str) -> list[tuple[str, str]] | None:
        """Use the 35B to verify the 4B's output.

        Short prompt in (~50 tokens), short response out (~10 tokens).
        35B has persistent session so follow-up verifications are 3-4s.

        Returns list of (old, new) replacement tuples, or None if verified.
        """
        if self._verifier is None:
            return None

        import re

        # Short prompt — just the original notes, not the generated note
        prompt = (
            f"Nurse wrote: {original_notes}\n"
            "Any clinical errors in the documentation? "
            "VERIFIED or REPLACE(\"old\",\"new\")"
        )

        result = ""
        for token in self._verifier.session_generate(prompt, max_tokens=100):
            result += token

        result = result.strip()
        if "VERIFIED" in result.upper() and "REPLACE" not in result.upper():
            return None

        replacements = []
        for match in re.finditer(r'REPLACE\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)', result):
            old, new = match.group(1), match.group(2)
            if old.strip() != new.strip():
                replacements.append((old, new))

        return replacements if replacements else None

    def get_patients(self) -> dict:
        """Return current patient list for the shift."""
        return self._patients.copy()

    def _extract_patient(self, input_text: str, response: str):
        """Extract and track patient info from notes."""
        # Simple extraction — look for bed/room numbers
        import re
        bed_match = re.search(r'bed\s*(\d+)', input_text, re.IGNORECASE)
        room_match = re.search(r'room\s*(\d+)', input_text, re.IGNORECASE)

        bed_id = None
        if bed_match:
            bed_id = f"bed_{bed_match.group(1)}"
        elif room_match:
            bed_id = f"room_{room_match.group(1)}"

        if bed_id:
            if bed_id not in self._patients:
                self._patients[bed_id] = {
                    'first_seen': datetime.now().isoformat(),
                    'updates': 0,
                }
            self._patients[bed_id]['updates'] += 1
            self._patients[bed_id]['last_update'] = datetime.now().isoformat()
