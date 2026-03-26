"""Use session_generate for everything — the way Kandiga actually works fast."""
import time
from kandiga.engine import KandigaEngine

writer = KandigaEngine(model_path="mlx-community/Qwen3.5-4B-4bit", fast_mode=True)
writer.load()
writer.start_session()

verifier = KandigaEngine(model_path="mlx-community/Qwen3.5-35B-A3B-4bit", fast_mode=True)
verifier.load()
verifier.start_session()

nurse = (
    "bed 4 johnson 78F post-op day 2 hip. vitals 128/82 hr 76 temp 98.4. "
    "wound clean dry intact. pain 4/10 tylenol. oriented x4 lungs clear. "
    "potassium 3.1 called dr patel kcl 40meq iv ordered."
)

# Step 1: Feed nurse input to 35B via session_generate (not session_feed)
print("35B reading nurse input...")
t0 = time.time()
for _ in verifier.session_generate(f"Nurse note: {nurse}", max_tokens=5):
    pass
print(f"Read: {time.time()-t0:.1f}s")

# Step 2: 4B writes note
print("\n4B writing...")
t0 = time.time()
note = ""
for token in writer.session_generate(f"Format as nursing assessment:\n{nurse}", max_tokens=500):
    note += token
print(f"4B: {time.time()-t0:.1f}s")

# Step 3: 4B condenses
print("\n4B condensing...")
t0 = time.time()
condensed = ""
for token in writer.session_generate("One line, facts only, no formatting:", max_tokens=50):
    condensed += token
print(f"Condensed in {time.time()-t0:.1f}s: {condensed.strip()[:80]}")

# Step 4: Feed condensed to 35B + ask verification — ONE message
print("\n35B verifying (follow-up)...")
t0 = time.time()
first = None
result = ""
for token in verifier.session_generate(
    f"AI documented: {condensed.strip()}. Match nurse note? VERIFIED or REPLACE(\"wrong\",\"right\")",
    max_tokens=30
):
    if first is None:
        first = time.time()
    result += token
    print(token, end="", flush=True)

ttft = (first - t0) if first else time.time() - t0
total = time.time() - t0
print(f"\n\nVerify TTFT: {ttft:.1f}s | Total: {total:.1f}s")

writer.end_session()
verifier.end_session()
