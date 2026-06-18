#!/usr/bin/env python3
"""v2 detector: same task, with the obvious general extraction improvements
(NOT tuned to individual items). Probes whether a *better* deterministic phi
clears certify-grade precision (~0.90)."""
import json, re, pathlib
from collections import Counter
WORDS={"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,
       "eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12}
SUPERSEDED=re.compile(r"(previous|prior|\bold\b|older|earlier|rejected|deprecat|"
  r"do not implement|don't implement|history|formerly|context only|left here|"
  r"outdated|superseded|no longer|~~|originally|initial draft|first draft|"
  r"old proposal|earlier draft)",re.I)
CURRENT=re.compile(r"(current|\bnow\b|new behavior|updated|post-|final|latest|as of|in effect)",re.I)
COUNT_UNITS=r"(?:retries|retry|attempts?|deliveries|times|shots?|tries|x)"
def current_lines(text):
    keep=[]
    for ln in text.splitlines():
        s=ln.strip()
        if not s: continue
        if SUPERSEDED.search(s) and "now" not in s.lower(): continue
        # strip "(was N)" / "was N" fragments from otherwise-current lines
        s=re.sub(r"\(?\bwas\s+[\w.]+\)?","",s,flags=re.I)
        keep.append(s)
    return "\n".join(keep)
def canon(tok,unit):
    n=WORDS.get(str(tok).lower())
    if n is None:
        try:n=float(tok)
        except: return None
    u=(unit or "").lower()
    if u in("ms","millisecond","milliseconds"):return("time",n)
    if u in("s","sec","secs","second","seconds"):return("time",n*1000)
    if u in("m","min","mins","minute","minutes"):return("time",n*60000)
    return("count",n)
PRIORITY={"p0":0,"p1":1,"p2":2,"p3":3,"critical":1,"highest":1,"high":2,"medium":3,"med":3,"low":4,"blocker":0}
def extract(field,text,ft):
    if ft!="structured": return None
    text=current_lines(text); low=text.lower()
    if re.search(r"priorit|severity|status|is_critical",field,re.I):
        if re.search(r"\btrue\b|\byes\b|is critical|critical",low):return("bool",1)
        if re.search(r"\bfalse\b|\bno\b|not critical",low):return("bool",0)
        for k,v in PRIORITY.items():
            if re.search(rf"\b{k}\b",low):return("enum",v)
    # arithmetic: "1 (initial/try/attempt) + up to N retries" -> N+1
    m=re.search(r"1\s*(?:initial|try|attempt|st try)?[^\d]{0,15}\+[^\d]{0,15}(?:up to\s*)?(\d+)\s*"+COUNT_UNITS,low)
    if m: return("count",int(m.group(1))+1)
    # explicit max attempts / total = N
    m=re.search(r"(?:max\s*attempts?|total(?:\s*attempts|\s*shots)?|maxattempts)\D{0,14}?(\d+)",low)
    if m: return("count",float(m.group(1)))
    # 'now X'
    m=re.search(r"\bnow\s+([\w.]+)\s*"+COUNT_UNITS+r"?",low)
    if m:
        v=canon(m.group(1),None)
        if v:return v
    # number + (time-unit | count-unit | bare)
    for tok,unit in re.findall(r"\b([\w.]+)\s*(ms|sec|secs|seconds|s|min|mins|minutes|m|"+COUNT_UNITS+r")?\b",text,re.I):
        if tok.lower() in WORDS or re.fullmatch(r"\d+(\.\d+)?",tok):
            u=unit if unit and unit.lower() in("ms","sec","secs","seconds","s","min","mins","minutes","m") else None
            v=canon(tok,u)
            if v:return v
    return None
def detect(it):
    a=extract(it["field"],it["source_a"],it.get("field_type","structured"))
    b=extract(it["field"],it["source_b"],it.get("field_type","structured"))
    if a is None or b is None or a[0]!=b[0]: return "unknown"
    return "agree" if abs(a[1]-b[1])<1e-9 else "disagree"
items=[json.loads(l) for l in pathlib.Path("corpus_merged.jsonl").read_text().splitlines() if l.strip()]
rows=[(it,detect(it),it["truth"]) for it in items]
def sc(sub,name):
    tp=sum(1 for it,p,t in sub if p=="disagree" and t=="disagree")
    fp=sum(1 for it,p,t in sub if p=="disagree" and t!="disagree")
    fn=sum(1 for it,p,t in sub if p!="disagree" and t=="disagree")
    pr=tp/(tp+fp) if tp+fp else float('nan'); rc=tp/(tp+fn) if tp+fn else float('nan')
    print(f"{name:18} n={len(sub):2d} precision={pr:.2f} recall={rc:.2f} (tp={tp} fp={fp} fn={fn})")
print("=== v2 detector ===")
sc(rows,"ALL"); sc([r for r in rows if r[0].get('field_type')=='structured'],"structured")
sc([r for r in rows if r[0].get('field_type')=='freetext'],"freetext")
print("FP traps:",dict(Counter(it.get('trap') for it,p,t in rows if p=='disagree' and t!='disagree')))
