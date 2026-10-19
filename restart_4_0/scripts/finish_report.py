"""Refresh the report after the already-running inference validator succeeds."""
import json, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for attempt in range(160):
    path=ROOT/'results/phase5/qa/validation.json'
    if path.exists() and json.loads(path.read_text()).get('status')=='PASS':
        subprocess.run([sys.executable,str(ROOT/'scripts/report.py')],check=True,cwd=ROOT.parent)
        print('Final five-phase report refreshed after validated inference.',flush=True)
        break
    time.sleep(45)
else:raise SystemExit('Inference not validated; the report retains its explicit pending status.')
