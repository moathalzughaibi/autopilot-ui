
import os, json, pandas as pd
PROC = "/workspace/data/processed"

def _sym_path(sym): 
    return os.path.join(PROC, f"{sym}_journal.json")

def load_journal(symbol: str) -> dict:
    p=_sym_path(symbol)
    if os.path.exists(p):
        try: 
            return json.load(open(p,"r",encoding="utf-8"))
        except Exception:
            pass
    return {"symbol":symbol,"events":[]}

def add_event(symbol: str, date=None, etype="note", note="", tags=None):
    from datetime import date as _d
    j = load_journal(symbol)
    if date is None:
        date = _d.today().isoformat()
    else:
        date = pd.to_datetime(date).date().isoformat()
    if isinstance(tags,str):
        tags=[t.strip() for t in tags.split(",") if t.strip()]
    tags = tags or []
    ev = {"date":date,"type":str(etype)[:24],"note":str(note)[:500],"tags":tags}
    j["events"].append(ev)
    p=_sym_path(symbol)
    json.dump(j, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    # history parquet
    hp = os.path.join(PROC,"journal_history.parquet")
    row = pd.DataFrame([{"Symbol":symbol, **ev}])
    if os.path.exists(hp):
        import pandas as _pd
        df = _pd.read_parquet(hp); df = _pd.concat([df,row], ignore_index=True)
    else:
        df = row
    df.to_parquet(hp, index=False)
    return ev
