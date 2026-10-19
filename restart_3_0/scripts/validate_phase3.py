"""Independent source, formula, join and feature-matrix checks."""
import json,math
from shapely.geometry import shape,Point
import phase3_common as c
R=c.ROOT;O=c.OUT

def main():
 for r in c.read(O/'qa/input_manifest.csv'):assert c.digest(R/r['file'])==r['sha256'],r['file']
 for side in (R/'data/raw/environment_acs2022').rglob('*.request.json'):
  raw=side.with_name(side.name.replace('.request.json','.json'));assert c.digest(raw)==json.loads(side.read_text())['sha256']
 attrs={}
 for p in (R/'data/raw/environment_acs2022/attributes').glob('*.json'):
  if '.request.' in p.name:continue
  table=json.loads(p.read_text())
  for vals in table[1:]:
   r=dict(zip(table[0],vals));key=''.join(r[k] for k in ['state','county','tract','block group']);attrs.setdefault(key,{}).update(r)
 panel={r['row_id']:r for r in c.read(R/'data/processed/atm_panel_2024_2025_full_year.csv')}
 raw={r['row_id']:r for r in c.read(O/'data/site_context_raw.csv')};features={r['row_id']:r for r in c.read(O/'data/features_primary.csv')};sens={r['row_id']:r for r in c.read(O/'data/features_sensitivity.csv')}
 assert len(panel)==2442 and set(panel)==set(raw)==set(features)==set(sens)
 spec=json.loads((R/'protocol/environment_variables.json').read_text())['features'];schema=json.loads((O/'data/feature_schema.json').read_text());assert len(schema['primary_predictors'])==9
 def equal(actual,expected):
  if expected is None:assert actual==''
  else:assert math.isclose(float(actual),expected,rel_tol=1e-12,abs_tol=1e-12)
 for key,p in panel.items():
  r=raw[key];a=attrs[r['acs_geoid_2022']] if r['acs_geoid_2022'] else {}
  for f in spec:
   for v in f['components']:
    for suffix in ['E','M','EA','MA']:assert r[v+suffix]==(a.get(v+suffix) or '')
   nums=[c.number(a.get(v+'E')) for v in f['components']];v=None
   if all(x is not None for x in nums):
    if 'denominator' in f:
     den=c.number(a[f['denominator']+'E']);v=sum(c.number(a[x+'E']) for x in f['numerator'])/den if den>0 else None
    elif 'subtract_from' in f:v=2022-nums[0] if 1600<=nums[0]<=2022 else None
    else:v=nums[0]
   equal(r[f['name']],v);pred=('log1p_' if f['transform']=='log1p' else '')+f['name'];equal(features[key][pred],math.log1p(v) if v is not None and f['transform']=='log1p' else v)
  equal(features[key]['log1p_background_primary'],math.log1p(float(p['background_primary_200_500m'])))
  equal(sens[key]['log1p_background_unfiltered'],math.log1p(float(p['background_unfiltered_200_500m'])))
 polys=[(f['properties']['GEOID'],shape(f['geometry'])) for f in json.loads((O/'data/acs2022_boundaries.geojson').read_text())['features']]
 checked=0
 for year in ['2024','2025']:
  for city in c.CITIES:
   sample=sorted([p for p in panel.values() if p['outcome_year']==year and p['city']==city],key=lambda r:r['row_id'])[:5]
   for p in sample:
    point=Point(float(p['longitude']),float(p['latitude']));hits=[g for g,poly in polys if poly.covers(point)];assert raw[p['row_id']]['acs_geoid_2022']==(hits[0] if len(hits)==1 else '');checked+=1
 c.save(O/'qa/validation.json',dict(status='PASS',rows=len(panel),primary_predictors=9,independent_formula_checks='all rows and components',brute_force_join_checks=checked,scientific_acceptance='exploratory; pending independent review'))
 print('PASS: source hashes, every feature formula, baseline values and',checked,'brute-force joins')
if __name__=='__main__':main()
