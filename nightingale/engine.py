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
    """

    DATA_DIR = os.path.expanduser("~/.nightingale")

    def __init__(self, model: str | None = None):
        self._kandiga = KandigaEngine(
            model_path=model,
            fast_mode=True,
        )
        self._patients: dict[str, dict] = {}  # bed_id -> patient info
        self._shift_start: str | None = None
        self._ready = False

        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.DATA_DIR, "shifts"), exist_ok=True)

    def start_shift(self):
        """Begin a new shift session."""
        self._kandiga.load()
        self._kandiga.start_session()
        self._shift_start = datetime.now().isoformat()
        self._patients = {}
        self._ready = True

        # Prime the model with clinical context
        primer = f"System: {SYSTEM_PROMPT}\n\nShift started at {self._shift_start}. Ready for patient documentation."
        # Feed system prompt into KV cache
        for _ in self._kandiga.session_generate(primer, max_tokens=20):
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
        self._patients = {}
        self._shift_start = None
        self._ready = False

    def document(self, text: str, format: str = "assessment"):
        """Generate clinical documentation from quick notes.

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

    def update_patient(self, text: str):
        """Quick update on an existing patient. Model has full shift context.

        Yields tokens of the response.
        """
        if not self._ready:
            raise RuntimeError("No active shift. Call start_shift() first.")

        prompt = f"Update for existing patient: {text}\n\nAdd this to the patient's documentation. Reference any previous notes from this shift."

        for token in self._kandiga.session_generate(prompt, max_tokens=512):
            yield token

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
