"""Package only artifacts owned by this phase 1–2 workflow."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
files=[ROOT/name for name in ['README.md','requirements.txt','query.json','sorted_data.csv',
    'export (1).json','export (2).json','export (3).json',
    'Research Execution Blueprint for a Background-Adjusted, Cross-City ATM-Site Crime Study.pdf']]
for folder in ['dfs','nyc','buffalo','rochester','boundaries','metadata','atm_history']:
    files.extend(p for p in (ROOT/'data/raw'/folder).rglob('*') if p.is_file())
for folder in ['data/processed','data/raw_tables','protocol','reports']:
    files.extend(p for p in (ROOT/folder).glob('*') if p.is_file() and p.name!='release_manifest.sha256')
for name in ['download_sources.py','download_atm_history.py','build_phase12.py','build_historical_panel.py',
             'make_deliverables.py','validate_phase12.py','package_phase12.py']:
    files.append(ROOT/'scripts'/name)
files=sorted(set(files))
validation=json.loads((ROOT/'reports/validation.json').read_text())
assert validation['status']=='PASS'
lines=[]
for p in files:
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    lines.append(f'{digest}  {p.relative_to(ROOT)}')
manifest=ROOT/'reports/release_manifest.sha256';manifest.write_text('\n'.join(lines)+'\n')
files.append(manifest)
archive=ROOT/'phase_1_2_package.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(ROOT/'phase_1_2_package.zip.sha256').write_text(f'{digest}  {archive.name}\n')
print(json.dumps({'archive':str(archive),'files':len(files),'bytes':archive.stat().st_size,'sha256':digest},indent=2))
