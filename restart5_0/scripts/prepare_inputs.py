"""Preserve verified inherited source bytes and record their provenance."""
import json,shutil
from common import *
def main():
 inherited=[]
 jobs=[(PROJECT/'data/raw/boundaries/cities.geojson',RAW/'boundaries/cities.geojson'),(PROJECT/'data/raw/atm_history/history_index.json',RAW/'atm_history/history_index_inherited.json')]
 jobs.append((PROJECT/'restart_2024_2025/data/processed/atm_panel_2024_2025_full_year.csv',RAW/'reference/previous_2024_2025_panel.csv'))
 for folder in ['data/raw/atm_history','data/raw/temporal_extension/atm_history']:
  jobs += [(p,RAW/'atm_history'/p.name) for p in sorted((PROJECT/folder).glob('dfs_*.csv'))]
 for source,target in jobs:
  side=Path(str(source)+'.request.json');meta=json.loads(side.read_text()) if side.exists() else {}
  if meta.get('sha256'):assert sha(source)==meta['sha256'],source
  target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():assert sha(target)==sha(source)
  else:shutil.copyfile(source,target)
  if side.exists():shutil.copyfile(side,Path(str(target)+'.request.json'))
  inherited.append({'source_file':str(source.relative_to(PROJECT)),'target_file':str(target.relative_to(ROOT)),'sha256':sha(source),'bytes':source.stat().st_size,'provenance':'inherited_prior_derived_comparison_only' if 'reference' in target.parts else 'inherited_official_archive','original_retrieved_utc':meta.get('retrieved_utc','unknown_not_reconstructed'),'original_sidecar_hash_verified':bool(meta.get('sha256'))})
 write('inherited_sources.csv',inherited);freeze();print('Verified inherited inputs:',len(inherited))
if __name__=='__main__':main()
