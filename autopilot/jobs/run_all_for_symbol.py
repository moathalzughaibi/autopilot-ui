import sys, json
from autopilot.pipe.liquidity import compute_liquidity
from autopilot.pipe.anomalies import detect
from autopilot.signals.score import score_symbol

sym = sys.argv[1] if len(sys.argv)>1 else "2010.SR"

print(f"== Liquidity → {sym} ==")
print(compute_liquidity(sym))

print(f"== Anomalies → {sym} ==")
print(detect(sym).tail(5))

print(f"== Score → {sym} ==")
print(json.dumps(score_symbol(sym), ensure_ascii=False, indent=2))
