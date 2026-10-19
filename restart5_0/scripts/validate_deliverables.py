"""Validate report/table consistency, links, deliverable schemas and human gates."""
import collections,json,re
from common import *
def main():
 required=['README.md','reports/phase_1_2_report.md','reports/methods.md','reports/quality_and_sensitivity.md','reports/lessons_from_previous_attempts.md','reports/reproduce.md','reports/atm_locations_map.html','reports/figures/exposure_coverage.png','reports/figures/exposure_coverage.svg','reports/figures/radius_sensitivity.png','reports/figures/radius_sensitivity.svg','reports/validation.json','reports/phase_status.json']
 for name in required:assert (ROOT/name).is_file() and (ROOT/name).stat().st_size>0,name
 validation=json.loads((REPORTS/'validation.json').read_text());status=json.loads((REPORTS/'phase_status.json').read_text());assert validation['status']=='PASS' and all(status[k]['computational_status']=='COMPLETE' for k in ['phase_1','phase_2']);assert not status['confirmatory_eligible']
 full=read(OUT/'atm_panel_full_year_2024_2025.csv');early=read(OUT/'atm_panel_partial_2023.csv');exact=read(OUT/'atm_panel_exact_supported_2023_2025.csv');combined=read(OUT/'atm_panel_continuity_2023_2025.csv');allrows=full+early+exact
 assert {p['row_id'] for p in combined}=={p['row_id'] for p in full+early} and len(combined)==len(full)+len(early)
 assert len(full)==status['phase_2']['full_year_site_years'] and len(early)==status['phase_2']['partial_2023_site_periods'] and len(exact)==status['phase_2']['exact_identity_sensitivity_rows']
 assert set(full[0])=={r['column'] for r in read(OUT/'data_dictionary.csv')}
 monthly=read(OUT/'atm_site_month_panel.csv');monthlysum=collections.defaultdict(collections.Counter);seen=set()
 for r in monthly:
  key=(r['annual_row_id'],r['month']);assert key not in seen;seen.add(key)
  assert r['month'][:4]==r['outcome_year'] and 0<int(r['supported_days_in_month'])<=31 and r['confirmatory_eligible']=='False'
  c=monthlysum[r['annual_row_id']];c['supported_days']+=int(r['supported_days_in_month'])
  for k,v in r.items():
   if '_count_' in k:c[k]+=int(v)
  for radius in [25,50,100]:assert int(r[f'primary_any_{radius}m'])==int(int(r[f'primary_count_{radius}m'])>0)
 for p in allrows:
  c=monthlysum[p['row_id']];assert c['supported_days']==int(p['supported_days'])
  for k,v in c.items():assert v==int(p[k]),(p['row_id'],k,v,p[k])
 assert set(monthlysum)=={p['row_id'] for p in allrows}
 assert all(r['month']>='2023-02' for r in monthly)
 earlyfeb=[r for r in monthly if r['cohort']=='address_continuity_partial_2023' and r['month']=='2023-02'];assert len(earlyfeb)==len(early) and all(r['supported_days_in_month']=='7' for r in earlyfeb)
 for r in read(OUT/'qa/sensitivity_summary.csv'):
  pp=[p for p in allrows if p['cohort']==r['cohort'] and p['outcome_year']==r['year'] and p['city']==r['city']];radius=r['radius_m']
  assert int(r['sites'])==len(pp);assert int(r['positive_sites'])==sum(int(p[f'primary_any_{radius}m']) for p in pp)
  assert int(r['event_site_links'])==sum(int(p[f'primary_count_{radius}m']) for p in pp)
  assert int(r['positive_nearest_only'])==sum(int(p[f'primary_nearest_count_{radius}m'])>0 for p in pp)
  assert int(r['boundary_clear_sites'])==sum(p['boundary_buffer_clear_500m']=='True' for p in pp)
  assert int(r['sites_with_unknown_background_availability'])==sum(p['background_has_unknown_availability']=='True' for p in pp)
  if r['city']=='Buffalo':assert int(r['rounding_scenario_definitely_positive'])<=int(r['positive_sites'])<=int(r['rounding_scenario_possibly_positive'])
 for r in read(OUT/'qa/research_review_gates.csv'):assert r['status']=='PENDING' and (ROOT/r['artifact']).exists()
 for r in read(OUT/'qa/manual_linkage_audit.csv'):assert r['reviewer_decision']=='PENDING' and (ROOT/r['source_file']).exists() and r['native_offense'].upper() in ['ROBBERY','BURGLARY']
 for r in read(OUT/'qa/facility_clusters.csv'):assert r['reviewer_decision']=='PENDING' and int(r['component_size'])>=2
 broken=[];links=0
 for p in ROOT.rglob('*.md'):
  for match in re.finditer(r'\[[^\]]+\]\(([^)]+)\)',p.read_text()):
   target=match.group(1).split('#')[0]
   if not target or '://' in target:continue
   links+=1
   if not (p.parent/target).exists():broken.append((str(p.relative_to(ROOT)),target))
 assert not broken,broken
 for name in ['exposure_coverage.png','radius_sensitivity.png']:assert (REPORTS/'figures'/name).read_bytes().startswith(b'\x89PNG')
 maptext=(REPORTS/'atm_locations_map.html').read_text();assert '__SITES__' not in maptext and '__GEO__' not in maptext and '<script src=' not in maptext
 # Hash the active amendments so scope changes are visible independently of the initial freeze.
 amendments=[{'file':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in sorted((ROOT/'protocol').glob('*amendment.md'))]
 savejson(REPORTS/'deliverable_validation.json',{'status':'PASS','required_files':len(required),'local_markdown_links_checked':links,'sensitivity_rows':len(read(OUT/'qa/sensitivity_summary.csv')),'continuity_rows':len(combined),'alternative_exact_rows':len(exact),'supported_site_months':len(monthly),'monthly_annual_reconciliation':'PASS','amendments':amendments,'human_approvals':'PENDING_not_inferred','offline_map':True})
 print('Deliverable validation PASS;',links,'local document links checked',flush=True)
if __name__=='__main__':main()
