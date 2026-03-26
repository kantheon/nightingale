"""Test: 4B writes full note + condensed facts. 35B verifies condensed only."""
import time
from kandiga.engine import KandigaEngine

writer = KandigaEngine(model_path="mlx-community/Qwen3.5-4B-4bit", fast_mode=True)
writer.load()
writer.start_session()

verifier = KandigaEngine(model_path="mlx-community/Qwen3.5-35B-A3B-4bit", fast_mode=True)
verifier.load()
verifier.start_session()
for _ in verifier.session_generate(
    "You verify clinical facts. Respond ONLY with VERIFIED or REPLACE(\"wrong\",\"right\"). Nothing else.",
    max_tokens=10
):
    pass

nurse = (
    "bed 4 johnson 78F post-op day 2 hip. vitals 128/82 hr 76 temp 98.4. "
    "wound clean dry intact. pain 4/10 tylenol. oriented x4 lungs clear. "
    "potassium 3.1 called dr patel kcl 40meq iv ordered."
)

# 4B writes full note
print("4B writing full note...")
t0 = time.time()
note = ""
for token in writer.session_generate(f"Format as nursing assessment:\n{nurse}", max_tokens=500):
    note += token
print(f"4B done: {time.time()-t0:.1f}s")

# 4B generates condensed facts (should be instant — already cached)
print("\n4B condensing...")
t0 = time.time()
condensed = ""
for token in writer.session_generate(
    "List only the clinical facts from that note in one line. No formatting. Just values.",
    max_tokens=80
):
    condensed += token
print(f"Condensed in {time.time()-t0:.1f}s")
print(f"Facts: {condensed.strip()}\n")

# 35B verifies condensed facts vs nurse input
print("35B verifying...")
t_verify_start = time.time()
verify_first = None
result = ""
for token in verifier.session_generate(
    f"Nurse wrote: {nurse}\nAI extracted: {condensed.strip()}\nErrors? VERIFIED or REPLACE(\"wrong\",\"right\")",
    max_tokens=50
):
    if verify_first is None:
        verify_first = time.time()
    result += token
    print(token, end="", flush=True)

verify_total = time.time() - t_verify_start
verify_ttft = (verify_first - t_verify_start) if verify_first else 0
print(f"\n\n35B TTFT: {verify_ttft:.1f}s | Total: {verify_total:.1f}s")

writer.end_session()
verifier.end_session()
