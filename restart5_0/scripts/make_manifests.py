"""Raw provenance and explicit data dictionary, including unused preserved inputs."""
import json,platform,subprocess,sys
from common import *
def description(k):
 exact={'row_id':('Unique cohort/site/year key; cohort identity is part of key','identifier'),'site_id':('SHA-256 prefix of city, normalized address and published coordinate pair; identity may fragment after movement','identifier'),'cohort':('Address continuity full year, or strict exact identity with any supported exposure','category'),'supported_days':('Days supported by adjacent monthly membership under continuity assumption; not observed operating days','days'),'calendar_days':('365 or 366 days in outcome year','days'),'full_year_supported':('Supported interval duration equals the entire calendar year','boolean'),'background_primary_200_500m':('Unique prior-year robbery/burglary cases at distance >200 and <=500 m with a valid report date before outcome-year start','cases'),'background_unfiltered_200_500m':('Unique prior-year robbery/burglary cases in annulus irrespective of reporting date','cases'),'background_missing_invalid_report':('Annular cases with missing/invalid report date or report date earlier than occurrence','cases'),'background_late_report':('Annular cases with usable report date on/after outcome-year start','cases'),'max_coordinate_drift_m':('Largest geodesic displacement from prior-December location across 14 unique-address snapshots','metres'),'annulus_fraction_inside_city':('Projected area of intersection of 200–500 m annulus and city polygon divided by annulus area; 64 segments per quadrant','fraction'),'boundary_distance_projected_m':('UTM distance to municipal polygon boundary; a diagnostic, not historical boundary evidence','metres'),'boundary_buffer_clear_500m':('Projected boundary distance >502 m, conservatively beyond the nominal 500 m background','boolean'),'strict_exact_identity_full_year':('Same normalized address and coordinates support every day without the 50 m continuity allowance','boolean'),'report_time_is_ingestion_proxy':('Buffalo created_at is used as a report proxy and is not a verified report time','boolean'),'longitude':('Individual annual site longitude at baseline for full-year cohort','decimal degrees WGS84'),'latitude':('Individual annual site latitude at baseline for full-year cohort','decimal degrees WGS84'),'outcome_year':('Calendar year of outcome; 2023 only has partial exposure','year'),'background_year':('Outcome year minus one, even for partial exposure rows','year'),'confirmatory_eligible':('Always false until independent source, construct, exposure and GIS review','boolean')}
 if k in exact:return exact[k]
 if k=='background_report_date_coverage':return ('Fraction of unfiltered annular cases with valid nonmissing report dates, including late ones; null when the annulus contains no observed cases','fraction')
 if k=='background_has_unknown_availability':return ('At least one prior-year annular case lacks usable reporting chronology; known-available count is not a complete baseline','boolean')
 if k=='background_measurement_status':return ('Incomplete report dates, unverified ingestion proxy, or report-filtered latest extract; none reconstructs an as-of database','category')
 if k in ['supported_start','supported_end_exclusive']:return ('Bounds of supported interval union; exact-identity rows may have internal gaps. See exact_exposure_intervals.csv and supported_interval_count','ISO date')
 if k=='supported_interval_count':return ('Number of disjoint supported intervals; one for address-continuity cohorts','intervals')
 if k.startswith('actual_'):return ('Intentionally null: actual operation dates/duration not observed','unknown')
 if k.startswith('rounding_scenario_'):return ('Buffalo-only count under +/- half-cell 0.001 degree rounding displacement; lower definitely within radius, upper possibly within. Conditional scenario excludes larger block-centroid error; blank elsewhere','cases')
 if k.startswith('primary_any_'):return ('Binary indicator of at least one qualifying case during supported outcome exposure within stated radius','boolean')
 if k.startswith('primary_reported_count_'):return ('Outcome count with usable report date before next calendar year; supports historical-label availability sensitivity','cases')
 if k.startswith('primary_nearest_count_'):return ('Outcome count assigned only to nearest eligible exposed site within this cohort/year; ties by site ID','cases')
 if k.startswith('multiple_match_count_'):return ('Outcome links whose case also lies within the stated radius of another eligible exposed site','links')
 if '_count_' in k:return ('Unique city-case count for stated category and radius during supported outcome exposure; zero is observed under available data','cases')
 return (k.replace('_',' '),'text')
def main():
 manifest=[];register=[]
 inherited={r['target_file'] for r in read(OUT/'inherited_sources.csv')}
 for p in sorted(RAW.rglob('*')):
  if not p.is_file():continue
  rel=str(p.relative_to(ROOT));unused=any(f'/crime/{s}/{y}/' in rel for s in CITIES.values() for y in range(2015,2022))
  manifest.append({'file':rel,'bytes':p.stat().st_size,'sha256':sha(p),'role':'preserved_superseded_ten_year_acquisition' if unused else 'active_input_or_source_discovery','provenance':'inherited' if rel.removesuffix('.request.json') in inherited else 'fresh_request_or_discovery'})
  if p.name.endswith('.request.json'):
   m=json.loads(p.read_text());register.append({'sidecar':rel,'source_file':rel.removesuffix('.request.json'),'url':m.get('url',''),'params':json.dumps(m.get('params',{}),sort_keys=True),'method':m.get('method','GET'),'retrieved_utc':m.get('retrieved_utc','unknown_not_reconstructed'),'status':m.get('http_status',m.get('status','unspecified')),'sha256':m.get('sha256',''),'use':manifest[-1]['role']})
 write('source_manifest.csv',manifest);write('source_register.csv',register)
 panels=read(OUT/'atm_panel_full_year_2024_2025.csv');write('data_dictionary.csv',[{'column':k,'description':description(k)[0],'unit':description(k)[1],'example':str(panels[0][k]),'null_rule':'unknown or not applicable; never replace by zero without field-specific justification'} for k in panels[0]])
 versions={}
 from importlib.metadata import version
 for package in ['numpy','scipy','shapely','pyproj','requests','pandas','matplotlib']:
  try:versions[package]=version(package)
  except Exception:pass
 savejson(REPORTS/'environment.json',{'python':sys.version,'platform':platform.platform(),'packages':versions})
 print('Manifest',len(manifest),'files;',len(register),'request sidecars',flush=True)
if __name__=='__main__':main()
