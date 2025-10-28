
import os, json, yaml
PROC="/workspace/data/processed"
CFG = "/workspace/data/autopilot/config/shariah.yaml"
def classify(symbol: str) -> dict:
    cfg = yaml.safe_load(open(CFG,"r",encoding="utf-8"))
    wl=set(cfg.get("whitelist",[]) or []); bl=set(cfg.get("blacklist",[]) or [])
    sector_ex = set(cfg.get("sector_exclusions",[]) or [])
    # جرّب قراءة القطاع من الأساسيات
    sec = None
    p = os.path.join(PROC, f"{symbol}_fundamentals.json")
    if os.path.exists(p):
        try: sec = (json.load(open(p)).get("sector") or "").strip()
        except Exception: pass
    status="UNKNOWN"; reasons=[]
    if symbol in bl: status, reasons = "OUT", ["blacklist"]
    elif sec and sec in sector_ex: status, reasons = "OUT", [f"sector:{sec}"]
    elif symbol in wl: status, reasons = "IN", ["whitelist"]
    out={"symbol":symbol,"status":status,"reasons":reasons,"sector":sec}
    json.dump(out, open(os.path.join(PROC, f"{symbol}_shariah.json"),"w"), ensure_ascii=False, indent=2)
    return out
