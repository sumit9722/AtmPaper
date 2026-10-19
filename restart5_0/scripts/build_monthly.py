"""Materialize exposure-supported site-months and reconcile with annual panels.

These are subdivisions of each annual cohort, not independent extra ATM sites.
Annual baseline counts are deliberately not replicated into monthly predictors.
"""
import collections,csv,datetime as dt
from common import *
import sys
sys.path.insert(0,str(PROJECT/'scripts'))
from large_artifacts import restore
def main():
 restore(['restart5_0/data/processed/event_atm_links.csv'])
 panels=[]
 for name in ['atm_panel_full_year_2024_2025.csv','atm_panel_partial_2023.csv','atm_panel_exact_supported_2023_2025.csv']:panels+=read(OUT/name)
 exact=collections.defaultdict(list)
 for r in read(OUT/'qa/exact_exposure_intervals.csv'):exact[(r['site_id'],r['outcome_year'])].append((r['start_inclusive'],r['end_exclusive']))
 monthly={}
 for p in panels:
  intervals=exact[(p['site_id'],p['outcome_year'])] if p['cohort']=='exact_identity_supported' else [(p['supported_start'],p['supported_end_exclusive'])]
  days=collections.Counter()
  for a,b in intervals:
   lo=dt.date.fromisoformat(a);end=dt.date.fromisoformat(b)
   while lo<end:
    monthend=dt.date(lo.year+1,1,1) if lo.month==12 else dt.date(lo.year,lo.month+1,1);hi=min(monthend,end);days[lo.strftime('%Y-%m')]+=(hi-lo).days;lo=hi
  assert sum(days.values())==int(p['supported_days'])
  for month,n in sorted(days.items()):
   r={'annual_row_id':p['row_id'],'site_id':p['site_id'],'cohort':p['cohort'],'city':p['city'],'outcome_year':p['outcome_year'],'month':month,'supported_days_in_month':n,'longitude':p['longitude'],'latitude':p['latitude'],'confirmatory_eligible':False}
   for radius in [25,50,100]:
    for prefix in ['primary','robbery','burglary','primary_reported','primary_nearest']:r[f'{prefix}_count_{radius}m']=0
   monthly[(p['row_id'],month)]=r
 with (OUT/'event_atm_links.csv').open() as f:
  for link in csv.DictReader(f):
   if link['role']!='outcome':continue
   r=monthly[(link['row_id'],link['event_date'][:7])]
   for radius in [25,50,100]:
    if float(link['distance_m'])<=radius:
     r[f'primary_count_{radius}m']+=1;r[f'{link["category"]}_count_{radius}m']+=1;r[f'primary_reported_count_{radius}m']+=link['report_available_by_cutoff']=='True';r[f'primary_nearest_count_{radius}m']+=link['nearest_eligible_site']=='True'
 for r in monthly.values():
  for radius in [25,50,100]:r[f'primary_any_{radius}m']=int(r[f'primary_count_{radius}m']>0)
 write('atm_site_month_panel.csv',[monthly[k] for k in sorted(monthly)])
 savejson(REPORTS/'monthly_build.json',{'status':'BUILT','site_month_rows':len(monthly),'interpretation':'Subdivisions of alternative annual exposure cohorts; never stack cohorts or treat months as independent annual sites','no_unobserved_months_zero_filled':True})
 print('Exposure-supported site-months:',len(monthly),flush=True)
if __name__=='__main__':main()
