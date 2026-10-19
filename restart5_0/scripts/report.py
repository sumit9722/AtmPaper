"""Generate descriptive tables, figures, review gates and reproduction documentation."""
import collections,csv,datetime as dt,html,json,math,os
import numpy as np
os.environ.setdefault('MPLCONFIGDIR','/tmp/atm_restart5_matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *

def table(rows,fields):
 def val(v):
  if v is None or v=='':return '—'
  if isinstance(v,float):return f'{v:.4f}'
  return str(v).replace('|','/').replace('\n',' ')
 return '| '+' | '.join(fields)+' |\n| '+' | '.join('---' for _ in fields)+' |\n'+'\n'.join('| '+' | '.join(val(r.get(k,'')) for k in fields)+' |' for r in rows)+'\n'
def md(name,text):(REPORTS/name).write_text(text)
def integer(r,k):return int(r[k]) if r.get(k) else 0

def main():
 validation=json.loads((REPORTS/'validation.json').read_text());assert validation['status']=='PASS'
 full=read(OUT/'atm_panel_full_year_2024_2025.csv');early=read(OUT/'atm_panel_partial_2023.csv');exact=read(OUT/'atm_panel_exact_supported_2023_2025.csv');summary=read(OUT/'city_summary.csv');availability=read(OUT/'city_year_availability.csv');quality=read(OUT/'qa/crime_quality_by_city_year.csv');acq=json.loads((REPORTS/'acquisition.json').read_text());assert acq['status']=='PASS'
 mainpanel=early+full;cohorts=['address_continuity_partial_2023','address_continuity_full_year','exact_identity_supported'];sensitivity=[]
 for cohort in cohorts:
  for year in YEARS:
   for city in CITIES:
    pp=[r for r in mainpanel+exact if r['cohort']==cohort and int(r['outcome_year'])==year and r['city']==city]
    if not pp:continue
    for radius in [25,50,100]:
     clear=[r for r in pp if r['boundary_buffer_clear_500m']=='True'];small=[r for r in pp if r.get('max_coordinate_drift_m') and float(r['max_coordinate_drift_m'])<=25]
     sensitivity.append({'cohort':cohort,'city':city,'year':year,'radius_m':radius,'sites':len(pp),'positive_sites':sum(integer(r,f'primary_any_{radius}m') for r in pp),'positive_reported_by_year_end':sum(integer(r,f'primary_reported_count_{radius}m')>0 for r in pp),'positive_nearest_only':sum(integer(r,f'primary_nearest_count_{radius}m')>0 for r in pp),'event_site_links':sum(integer(r,f'primary_count_{radius}m') for r in pp),'multiply_matched_links':sum(integer(r,f'multiple_match_count_{radius}m') for r in pp),'boundary_clear_sites':len(clear),'boundary_clear_positive':sum(integer(r,f'primary_any_{radius}m') for r in clear),'drift_le_25m_sites':len(small) if cohort!='exact_identity_supported' else '', 'drift_le_25m_positive':sum(integer(r,f'primary_any_{radius}m') for r in small) if cohort!='exact_identity_supported' else '', 'rounding_scenario_definitely_positive':sum(integer(r,f'rounding_scenario_lower_count_{radius}m')>0 for r in pp) if city=='Buffalo' else '', 'rounding_scenario_possibly_positive':sum(integer(r,f'rounding_scenario_upper_count_{radius}m')>0 for r in pp) if city=='Buffalo' else '', 'sites_with_unknown_background_availability':sum(r['background_has_unknown_availability']=='True' for r in pp),'background_missing_invalid_links':sum(integer(r,'background_missing_invalid_report') for r in pp),'background_total_links':sum(integer(r,'background_unfiltered_200_500m') for r in pp)})
 write('qa/sensitivity_summary.csv',sensitivity)
 # Source-vintage comparison matched by city/address/coordinates, not hash convention.
 prior=RAW/'reference/previous_2024_2025_panel.csv';comparisons=[]
 if prior.exists():
  old=read(prior);key=lambda r:(r['city'],r['outcome_year'],norm(r['address_raw']),float(r['longitude']),float(r['latitude']));oldmap={key(r):r for r in old};newmap={key(r):r for r in full}
  for year in [2024,2025]:
   for city in CITIES:
    ok={k:v for k,v in oldmap.items() if k[0]==city and k[1]==str(year)};nk={k:v for k,v in newmap.items() if k[0]==city and k[1]==str(year)};shared=ok.keys()&nk.keys()
    comparisons.append({'city':city,'year':year,'previous_sites':len(ok),'new_sites':len(nk),'matched_locations':len(shared),'added_locations':len(nk.keys()-ok.keys()),'removed_locations':len(ok.keys()-nk.keys()),'changed_50m_counts':sum(ok[k]['primary_count_50m']!=nk[k]['primary_count_50m'] for k in shared),'changed_background_counts':sum(ok[k]['background_primary_200_500m']!=nk[k]['background_primary_200_500m'] for k in shared),'interpretation':'Fresh source vintage plus documented report chronology/source completeness changes; not model improvement'})
 write('qa/prior_release_comparison.csv',comparisons,['city','year','previous_sites','new_sites','matched_locations','added_locations','removed_locations','changed_50m_counts','changed_background_counts','interpretation'])
 gates=[{'gate':'Construct and offense mapping','status':'PENDING','required_evidence':'Independent crime-domain adjudication of robbery/burglary codebook, attempts and case-level duplicate rule','artifact':'data/processed/crime_codebook.csv'}, {'gate':'Facility identity and continuity','status':'PENDING','required_evidence':'Review unique-address matching, coordinate drift, institution changes and nearby facilities; monthly listings do not prove actual operation','artifact':'data/processed/qa/continuity_eligibility.csv'}, {'gate':'Incident-site linkage','status':'PENDING','required_evidence':'Independent adjudication of stratified event-site audit with reasoned accept/reject decisions','artifact':'data/processed/qa/manual_linkage_audit.csv'}, {'gate':'Buffalo coordinates','status':'PENDING','required_evidence':'Better incident coordinates or approved coarser design; 50 m results are exploratory','artifact':'data/processed/qa/sensitivity_summary.csv'}, {'gate':'Temporal availability and reporting','status':'PENDING','required_evidence':'Validate Buffalo created_at proxy and missing timestamps; current revisions do not recreate historical availability','artifact':'data/processed/qa/crime_quality_by_city_year.csv'}, {'gate':'Historical boundaries and selection','status':'PENDING','required_evidence':'Verify municipal vintage and selection from survival/unique-address restrictions; inspect boundary sensitivity','artifact':'data/processed/city_year_availability.csv'}, {'gate':'Scientific approval and later modeling','status':'PENDING','required_evidence':'PI approval of construct, practical-effect threshold and features; independent later holdout still required','artifact':'protocol/study_spec.md'}]
 write('qa/research_review_gates.csv',gates)
 audits=read(OUT/'qa/manual_linkage_audit.csv');wanted={r['event_id'] for r in audits};references={}
 with (OUT/'crime_primary_2022_2025.csv').open() as f:
  for r in csv.DictReader(f):
   if r['event_id'] in wanted:references[r['event_id']]=r
 panelmap={r['row_id']:r for r in mainpanel+exact}
 for r in audits:
  e=references[r['event_id']]
  for k in ['source_file','source_row_index','native_offense','native_description','attempt_status']:r[k]=e[k]
  r['site_address']=panelmap[r['row_id']]['address_raw']
 write('qa/manual_linkage_audit.csv',audits)
 # Facility connected components from audited pairs; distinct addresses remain distinct sites.
 parents={}
 def find(x):
  parents.setdefault(x,x)
  while parents[x]!=x:parents[x]=parents[parents[x]];x=parents[x]
  return x
 for r in read(OUT/'qa/facility_review.csv'):
  a=(r['cohort'],r['outcome_year'],r['site_a']);b=(r['cohort'],r['outcome_year'],r['site_b']);ra,rb=find(a),find(b)
  if ra!=rb:parents[max(ra,rb)]=min(ra,rb)
 components=collections.defaultdict(list)
 for k in parents:components[find(k)].append(k)
 clusters=[]
 for root,members in sorted(components.items()):
  for cohort,year,id in sorted(members):clusters.append({'cohort':cohort,'outcome_year':year,'site_id':id,'facility_cluster_id':'fc_'+hashlib.sha256(str(sorted(members)).encode()).hexdigest()[:16],'component_size':len(members),'interpretation':'connected <=10m pairs; not an automatically merged facility','reviewer_decision':'PENDING'})
 write('qa/facility_clusters.csv',clusters,['cohort','outcome_year','site_id','facility_cluster_id','component_size','interpretation','reviewer_decision'])
 # Reproducible source investigation evidence.
 archive_evidence=[]
 for name in ['dfs_version1','dfs_version200','dfs_version247']:
  obj=json.loads((RAW/f'discovery/{name}.json').read_text());archive_evidence.append({'requested_version':name.removeprefix('dfs_version'),'returned_version':obj.get('value',{}).get('version'),'interpretation':'Request resolves to oldest exposed version; cannot label it as an earlier snapshot'})
 write('qa/archive_resolution_audit.csv',archive_evidence)
 # Static export-quality figures.
 figdir=REPORTS/'figures';figdir.mkdir(exist_ok=True)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'restart5_0'})
 fig,axes=plt.subplots(1,2,figsize=(12,4.3),constrained_layout=True)
 years=[2023,2024,2025];colors=['#e7a44b','#217c89','#215d91'];totalrows=[sum(int(r['outcome_year'])==y for r in mainpanel) for y in years]
 axes[0].bar([str(y) for y in years],totalrows,color=colors)
 for i,(n,days) in enumerate(zip(totalrows,[313,366,365])):axes[0].text(i,n+15,f'{n:,} sites\n{days} supported days',ha='center',va='bottom',fontsize=10)
 axes[0].set(ylim=(0,max(totalrows)*1.22),ylabel='Address-continuity sites',title='Maximum recovered annual exposure')
 for i,c in enumerate(CITIES):
  counts=[next(int(r['full_year_sites']) if r['full_year_sites'] else 0 for r in availability if r['city']==c and r['outcome_year']==str(y)) for y in [2024,2025]]
  axes[1].plot([2024,2025],counts,'o-',label=c)
 axes[1].set(xticks=[2024,2025],ylabel='Full-year cohort sites',title='Full-year denominators by city');axes[1].legend(frameon=False)
 fig.savefig(figdir/'exposure_coverage.png',dpi=180);fig.savefig(figdir/'exposure_coverage.svg',metadata={'Date':None});plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(12,4),constrained_layout=True)
 for ax,city in zip(axes,CITIES):
  rr=[r for r in sensitivity if r['cohort']=='address_continuity_full_year' and r['city']==city]
  for y,color in [(2024,'#217c89'),(2025,'#c66d2b')]:
   ss=sorted([r for r in rr if r['year']==y],key=lambda r:r['radius_m']);ax.plot([r['radius_m'] for r in ss],[r['positive_sites']/r['sites'] for r in ss],'o-',label=str(y),color=color)
  ax.set(title=city,xticks=[25,50,100],xlabel='Outcome radius (m)',ylim=(0,1));ax.legend(frameon=False)
 axes[0].set_ylabel('Sites with ≥1 nearby robbery/burglary');fig.suptitle('Descriptive sensitivity; these are not model results',fontsize=13)
 fig.savefig(figdir/'radius_sensitivity.png',dpi=180);fig.savefig(figdir/'radius_sensitivity.svg',metadata={'Date':None});plt.close(fig)
 # Offline map: SVG municipal outlines, selected year, hover details. No basemap or remote scripts.
 geo=json.loads((RAW/'boundaries/cities.geojson').read_text());mapdata=[{k:r[k] for k in ['city','longitude','latitude','outcome_year','supported_days','address_raw','primary_count_50m','background_measurement_status']} for r in mainpanel]
 template='''<!doctype html><meta charset="utf-8"><title>Restart 5.0 — ATM exposure map</title><style>body{font:16px system-ui;margin:30px;color:#172d3e;background:#f6f8f9}h1{font-size:25px}.maps{display:flex;gap:16px;flex-wrap:wrap}.city{background:white;padding:12px;border:1px solid #ccd4da;border-radius:8px}svg{width:360px;height:420px}circle{cursor:help}select{font:inherit;padding:7px}p{max-width:1050px}</style><h1>ATM sites with supported exposure</h1><p>2023: 22 February–31 December (313 days). 2024 and 2025: full calendar years. Hover over a site for its address and descriptive counts. Nearby crime is not verified ATM-targeted crime. Buffalo coordinates and reporting times require review.</p><label>Outcome year <select id="year"><option>2023</option><option>2024</option><option selected>2025</option></select></label><div class="maps" id="maps"></div><script>const sites=__SITES__,geo=__GEO__;const ns='http://www.w3.org/2000/svg';function node(t,a={}){let n=document.createElementNS(ns,t);for(let k in a)n.setAttribute(k,a[k]);return n}function render(){let year=document.getElementById('year').value,root=document.getElementById('maps');root.replaceChildren();for(let city of ['New York City','Buffalo','Rochester']){let feature=geo.features.find(f=>(f.properties.BASENAME==='New York'?'New York City':f.properties.BASENAME)===city),polys=feature.geometry.type==='MultiPolygon'?feature.geometry.coordinates:[feature.geometry.coordinates],pts=polys.flat(2),cos=Math.cos(pts[0][1]*Math.PI/180),xx=pts.map(p=>p[0]*cos),yy=pts.map(p=>p[1]),xmin=Math.min(...xx),xmax=Math.max(...xx),ymin=Math.min(...yy),ymax=Math.max(...yy),scale=Math.min(330/(xmax-xmin),385/(ymax-ymin)),project=p=>[15+(p[0]*cos-xmin)*scale,400-(p[1]-ymin)*scale];let box=document.createElement('div');box.className='city';let title=document.createElement('h2');title.textContent=city;box.append(title);let svg=node('svg',{viewBox:'0 0 360 420'});for(let poly of polys){let path=poly.map(r=>r.map((p,i)=>(i?'L':'M')+project(p).join(' ')).join(' ')+'Z').join(' ');svg.append(node('path',{d:path,fill:'#eaf0f2',stroke:'#a1b0ba','fill-rule':'evenodd'}))}let ss=sites.filter(s=>s.city===city&&s.outcome_year===year);for(let s of ss){let [cx,cy]=project([+s.longitude,+s.latitude]),dot=node('circle',{cx,cy,r:city==='New York City'?2:3,fill:+s.primary_count_50m?'#b85f2b':'#167c85',opacity:.8}),tip=node('title');tip.textContent=s.address_raw+' | '+s.supported_days+' supported days | '+s.primary_count_50m+' nearby cases within 50 m | '+s.background_measurement_status;dot.append(tip);svg.append(dot)}box.append(svg);let count=document.createElement('p');count.textContent=ss.length+' sites; orange = ≥1 nearby case';box.append(count);root.append(box)}}document.getElementById('year').addEventListener('change',render);render();</script>'''
 (REPORTS/'atm_locations_map.html').write_text(template.replace('__SITES__',json.dumps(mapdata).replace('</','<\\/')).replace('__GEO__',json.dumps(geo).replace('</','<\\/')))
 main_summary=[r for r in summary if r['cohort'].startswith('address_continuity') and r['site_years']]
 main_table=table(main_summary,['city','outcome_year','site_years','supported_site_days','positive_50m','prevalence_50m'])
 rawactive=sum(r['downloaded_rows'] for r in acq['partitions'] if r['year']>=2022)+sum(r['downloaded_rows'] for r in acq.get('late_report_supplements',[]))
 md('phase_1_2_report.md',f'''# Restart 5.0 — phases 1 and 2

The user replaced the original ten-year request with the longest recovered continuous ATM snapshot period. **Both computational phases are complete and validated for that revised scope.** Independent scientific acceptance remains pending. No predictive models were fitted.

## Period and denominator

Thirty-six monthly DFS snapshots cover **22 February 2023–15 January 2026**. This supports **2024 and 2025 as complete calendar years**, plus a separately labeled **313-day 2023 cohort** (22 February–31 December). The source investigation does not establish that older records cannot exist elsewhere; it establishes the longest continuous series recovered from the assessed public sources. The current public archive resolves requested versions 1, 200 and 247 to version 248, dated February 2023 in the saved index. Two indexed Wayback captures (April 2021 and November 2022) are isolated and do not establish monthly continuity. Future incomplete 2026 outcomes cannot add a third complete year as of this release.

The primary annual location follows a unique normalized city/address across all required monthly snapshots, with displacement no greater than 50 m from the initial coordinate. Each year is selected separately. This retains **{len(full):,} full-year site-years** and **{len(early):,} partial-2023 site-periods**. The combined continuity file has **{len(mainpanel):,} rows**. A separate exact-coordinate sensitivity has **{len(exact):,} supported identity-years** and may split a physical facility after a coordinate revision. Never stack these alternative cohorts or interpret their combined row count as independent ATMs.

{main_table}

The 2023 binary prevalence is based on 313 days and is not directly comparable to annual prevalence. Full-year restriction and address/coordinate stability can select a nonrepresentative subset. Actual operation and opening/closing dates remain unknown.

## Phase 1 — construct and study design

The [working specification](../protocol/study_spec.md) freezes three municipalities, bank-owned/in-bank DFS locations, robbery/burglary, a 50 m endpoint with 25/100 m sensitivities, and a previous-year >200–500 m baseline. It distinguishes nearby incidents from attacks on machines, report availability from latest occurrence records, and computational completion from independent approval. The [scope amendment](../protocol/scope_amendment.md) preserves the user's change of direction. Source-completeness and partial-2023 amendments document subsequent data-quality work. The original protocol and hash are retained as superseded records.

The observed native [crime codebook](../data/processed/crime_codebook.csv), [data dictionary](../data/processed/data_dictionary.csv), [source register](../data/processed/source_register.csv), [lessons from previous attempts](lessons_from_previous_attempts.md), [later-phase analytical commitments](../protocol/future_analysis_plan.md), and explicit review gates complete the computational construct deliverables. The plan specifies M0/M1/M2, metrics, temporal/spatial evaluation, matched transfer controls and uncertainty; none is fitted here. This is a retrospective working protocol, not a signed preregistration.

## Phase 2 — sources, exposure and linkage

The active 2022–2025 extracts contain **{rawactive:,} source rows**, reconciled against API counts or exact ArcGIS object IDs. After exclusions and global city-case deduplication, **{validation['all_unique_events']:,} unique valid cases** remain, including **{validation['primary_events']:,} robbery/burglary cases**. There are **{validation['excluded_rows']:,} excluded source rows** and **{validation['duplicate_rows']:,} duplicate case rows**, all retained with reasons. NYC extracts contain primary categories only; Buffalo and Rochester preserve their broader published categories for audit, not a comparable all-crime endpoint. 2022 supplies background only. Earlier raw crime acquired under the abandoned ten-year design is preserved but not analyzed.

The NYC current-year feed adds {sum(r['downloaded_rows'] for r in acq['late_report_supplements'])} earlier-occurrence records, including {next(r['downloaded_rows'] for r in acq['late_report_supplements'] if r['year']==2025)} dated 2025. These are included in occurrence-based outcomes and excluded by the applicable reporting cutoff from historical predictors/labels. Current feed coverage is quarterly and source updates differ across cities; no claim of eventual final counts or a historical as-of database is made.

ATM coordinates are assigned to archived Census municipal polygons. Exact duplicate locations collapse, distinct neighboring addresses remain separate and receive facility review pairs/components. Events are deduplicated by city case with robbery > burglary > other, later occurrence, and deterministic source order. All dropped rows and conflicts remain auditable.

The release saves **{validation['link_rows']:,} event-site links across the alternative cohorts**. Candidate search is conservative UTM; every final distance uses the WGS84 ellipsoid. Outcomes in partial cohorts require supported exposure on the event date. A case can link to multiple sites; multiplicity and nearest-eligible-site sensitivities are explicit. Previous-year backgrounds exclude <=200 m and require a usable reporting date before the outcome year. Missing/invalid and late reporting are separate columns. Buffalo created_at remains an ingestion proxy. The [site-month table](../data/processed/atm_site_month_panel.csv) materializes supported monthly days and outcome counts and reconciles back to each annual row; unsupported months are absent, not zero-filled.

## Validation and limits

Independent validation passed {len(validation['checks'])} check groups: raw hashes, source-row conservation, monthly grids, raw-snapshot cohort reconstruction, every supported exposure day, every link distance, report cutoffs, count reconciliation, multiplicity/nearest assignment, and sampled direct geodesic searches that bypass the spatial index. See [validation.json](validation.json).

The [quality and sensitivity report](quality_and_sensitivity.md) quantifies the most material limitations: coordinate revisions leave no strict exact-coordinate full-year 2024 sites; Buffalo earlier reporting timestamps are extensively missing; its incident coordinates sit on a 0.001-degree grid; and boundary clipping can truncate nearby context. Review decisions remain PENDING, and confirmatory_eligible is false. A successful computational check cannot resolve these source limitations or provide independent scientific approval.

[Reproduce](reproduce.md) · [Methods](methods.md) · [Map](atm_locations_map.html) · [Exposure figure](figures/exposure_coverage.png) · [Radius sensitivity](figures/radius_sensitivity.png)
''')
 md('methods.md','''# Methods and interpretation

The primary construct is future nearby police-recorded robbery/burglary at a bank-owned/in-bank ATM location. No event is asserted to target a machine. Units are annual site-periods with separately documented exposure duration. The 2023 partial cohort is a duration-annotated extension; it is not a full-year zero-filled backcast.

## Exposure and location

Full-year cohorts require fourteen monthly observations: previous December through following January, all unique for city/normalized address and within 50 m of the initial point. The 2023 partial cohort applies the same spatial and identity rule to twelve observations beginning 22 February; only 313 days are supported. There are no extrapolated January/early-February outcomes. Each year is assembled independently, avoiding a requirement to survive throughout all study years.

The exact-identity sensitivity intersects membership between adjacent monthly snapshots, requires a single-month step and a gap <=62 days, clips to the calendar year, and merges touching intervals. Its row-level start/end fields bound the union; they do not imply uninterrupted exposure if supported_interval_count exceeds one. The authoritative exact interval union is qa/exact_exposure_intervals.csv. Actual operating duration is unknown for every cohort.

The prior-year annulus is calculated at that period's fixed site coordinate, irrespective of whether the ATM was present in the baseline year; it describes surrounding place context. All input events are clipped to the same municipal polygon, so background and even outcome neighborhoods can be truncated near a boundary. Annulus coverage is a diagnostic in the city-specific UTM projection, using 64 polygon segments per quadrant. The boundary-clear sensitivity excludes sites within 502 projected metres of the polygon edge.

## Case, date and source rules

NYC historical and current-year feeds are joined using their persistent complaint identifiers. Buffalo uses case_number and Rochester Case_Number. Only primary categories are an aligned NYC extraction; other cities' nonprimary rows support quality audits. The city-case hierarchy is robbery > burglary > other, later occurrence, then deterministic source-file/index order. Conflicts remain in the duplicate queue; this convention is subject to independent review.

Rochester epoch times are converted to America/New_York before date assignment. NYC and Buffalo date strings retain source local-date semantics. Report dates earlier than occurrence are marked invalid. Report filtering uses calendar dates strictly before January 1; unknown or invalid reporting times never count as known-available. NYC current-year late-report supplementation prevents treating the historical feed alone as a complete current occurrence-year extract. Eventual reporting and revision remain incomplete and heterogeneous across cities.

Buffalo created_at is an ingestion timestamp, not a validated date first reported to police. Missing timestamps create incomplete baseline availability. background_has_unknown_availability and background_measurement_status prevent interpreting a known-available count of zero as proof of no actual surrounding crime. No modeling is performed here.

## Geodesic linkage and sensitivities

Candidate lookup uses EPSG:32618 for New York City and EPSG:32617 for Buffalo/Rochester, with a 502 m radius. WGS84 geodesics determine all final <=25/50/100 m outcomes and >200/<=500 m backgrounds. For partial rows an event must also fall in the supported interval union. Nearest-site flags rank eligible exposed sites separately for each cohort/year/event; ties use site ID. The full-year and sensitivity cohorts intentionally overlap and are never combined for inference.

Buffalo's rounding scenario perturbs an event by at most the geodesic diagonal of a half-cell (0.0005 degrees in each coordinate). Distance plus that amount <=radius is definitely inside under this hypothetical scenario; distance minus that amount <=radius is possibly inside. The scenario does not bound block-centroid displacement, ATM-location error or systematic geocoding error. It is not a confidence interval, correction, or evidence that 50 m inference is defensible.

The study remains exploratory: earlier releases exposed 2024/2025 outcomes; known-available reporting does not reconstruct a historical source vintage; full-year stability can induce selection; and partial-year prevalence differs in observation duration. Later environmental modeling requires ex-ante feature provenance, a new analysis specification, rolling-origin temporal checks with repeated-site/spatial safeguards, and explicit handling of incomplete baselines. Prior nearby crime measures temporal persistence and must be distinguished from environmental increment.
''')
 fullsens=[r for r in sensitivity if r['cohort']=='address_continuity_full_year' and r['radius_m']==50]
 buffaloq=[r for r in quality if r['city']=='Buffalo'];buffalos=[r for r in sensitivity if r['city']=='Buffalo' and r['radius_m']==50 and r['cohort']!='exact_identity_supported']
 md('quality_and_sensitivity.md',f'''# Quality audit and descriptive sensitivities

## Reporting completeness

{table(buffaloq,['year','primary_cases','missing_invalid_report_primary','reported_after_year_primary','primary_coordinates_on_3dp_grid'])}

The missing/invalid count is a record-level audit. Site baselines use the preceding year, so missing 2023 dates affect 2024 prediction inputs. These missing dates are excluded from known-available counts, never silently filled. Even nonmissing Buffalo timestamps remain unverified ingestion proxies.

## Exposure attrition and coordinate movement

{table(availability,['city','outcome_year','available_snapshots','inventory_identities','full_year_sites','drift_10m_full_year_sites','drift_25m_full_year_sites','exact_full_year_sites'])}

A blank 2023 full-year count means unsupported coverage, not zero ATMs. Strict exact identity yields no full-year 2024 cohort; the working 50 m address-continuity rule is therefore a substantive assumption. Smaller drift cutoffs show its effect. Exact identities can fragment physical facilities, which explains why the exact-supported panel has many more rows than the continuity panel. Annual cohorts and reference coordinates differ: the radius figure is not an identified time trend or evidence that crime risk changed at unchanged facilities.

## Full-year 50 m sensitivities

{table(fullsens,['city','year','sites','positive_sites','positive_reported_by_year_end','positive_nearest_only','event_site_links','multiply_matched_links','boundary_clear_sites','boundary_clear_positive','sites_with_unknown_background_availability'])}

Repeated event-site links are not independent crimes. Nearest-only and boundary-clear results are descriptive alternatives; no sensitivity has been selected by model performance. Radius-specific results for every cohort are in sensitivity_summary.csv and the radius figure.

## Buffalo conditional rounding scenario

{table(buffalos,['year','sites','positive_sites','rounding_scenario_definitely_positive','rounding_scenario_possibly_positive'])}

The range above is conditional on rounding error alone. Block-address geocoding can introduce larger displacement, so these columns do not repair positional uncertainty or license confirmatory 50 m claims.

## Comparison with the earlier 2024–2025 data release

{table(comparisons,['city','year','previous_sites','new_sites','matched_locations','changed_50m_counts','changed_background_counts'])}

Location matching uses city, normalized address, numerical coordinates and year, not the changed hash formatting. Differences are source-vintage and documented data-rule differences. The previous release remains preserved. Do not attribute changed descriptive counts to prediction improvement.

## Independent review

{table(gates,['gate','status','required_evidence'])}

The review queues include source references, geodesic distances, strata and blank reviewer fields. Automatic validation is complete; human adjudication has not occurred.
''')
 md('lessons_from_previous_attempts.md','''# Lessons applied from previous attempts

| Previous evidence or failure mode | Restart 5.0 response | Inspectable evidence |
| --- | --- | --- |
| The original current ATM list was unsuitable as a historical denominator. | Recovered continuous monthly archives set the analysis period; partial exposure remains explicit. | required_atm_months.csv, exposure intervals, scope amendment |
| The desired decade exceeded available exposure history. | User-directed scope replacement before build; preserve initial protocol and downloads. | superseded_ten_year_spec.md and both freeze records |
| Public archive requests can resolve older requested versions to the oldest retained version. | Inspect returned versions; never misdate a substituted export. | archive_resolution_audit.csv and raw discovery responses |
| Exact coordinates changed during 2024 and eliminated its strict full-year cohort. | Keep strict sensitivity; apply an auditable unique-address <=50 m rule with 10/25 m attrition sensitivity. | continuity links/eligibility and exact inventory |
| Earlier pipelines treated completed computations as a stronger milestone than source validity justified. | Separate computational PASS from independent scientific acceptance and confirmatory eligibility. | phase_status.json and research_review_gates.csv |
| Earlier incomplete offset extraction had to be isolated. | Partition source downloads by year, reconcile API counts before/after and unique source IDs; ArcGIS batches reconcile exact IDs. | acquisition.json, raw request sidecars, validation.json |
| Historical NYPD data is organized by reporting coverage, not an eventually final occurrence-year census. | Add earlier occurrences from the current-year feed; preserve/report late cases separately. | late_current raw partitions and source-completeness amendment |
| Buffalo created_at is a proxy, and missing earlier report times can materially deplete background counts. | Explicit incomplete-availability flags and coverage fraction; no inference that missing reports mean no crime. | crime quality and background_measurement_status |
| Public Buffalo coordinates are rounded on a grid larger than the 50 m endpoint's scale. | Quantify rounding and a conditional displacement scenario; retain an unresolved precision gate. | sensitivity summary and quality report |
| Crime was counted at multiple nearby sites. | Save multiplicity and nearest-exposed-site sensitivity per cohort/year; identify facility components separately. | event links and facility review |
| Municipality clipping can truncate surrounding context. | Quantify annulus coverage and boundary distance; publish boundary-clear sensitivity. | panel geometry diagnostics and sensitivity summary |
| Previous 4.0 improvement came mainly from prior nearby crime, not necessarily an environmental effect. | Keep environmental increment and temporal persistence conceptually separate in future-phase guardrails. | active study specification |
| Both earlier outcome years have already been inspected. | Do not call this preregistered or an untouched confirmatory test; no models or significance target in phases 1–2. | protocol and status |
| Automated validation can reproduce a shared implementation mistake. | Independent raw-snapshot reconstruction, source conservation, direct geodesic omission checks and count replay. | validate.py and validation.json |

The new release preserves earlier directories and does not reuse their PASS statuses as evidence. The raw source bytes inherited from previous work are separately identified and hash checked; fresh crime and February–November 2023 ATM retrievals are not mislabeled as inherited.
''')
 md('reproduce.md','''# Reproduction

From the repository root, use the existing environment:

```bash
.venv/bin/python restart5_0/scripts/run_all.py
```

This is an offline rebuild from restart5_0/data/raw. It requires no model fitting and does not rewrite earlier releases. It verifies current raw input hashes and the stored parts of the large link table before rebuilding, then rebuilds crime normalization, exposure, panels, manifests, independent validation and reports. A failure stops the run. The final artifact manifest hashes stored derived tables, protocol, scripts, reports and figures, excluding the manifest itself. The large link CSV is regenerated locally and checked against the checksum in ../large_artifacts.json; its tracked byte parts are included in the manifest. Input retrieval timestamps remain fixed; environment metadata may differ on another machine.

For direct inspection on a fresh checkout, run `python3 scripts/large_artifacts.py restore restart5_0/data/processed/event_atm_links.csv` from the repository root. This concatenates the tracked parts and verifies the exact original SHA-256. The complete CSV is intentionally ignored by Git.

Python dependencies are in restart5_0/requirements.txt; exact installed versions and Python version are recorded in reports/environment.json. The existing environment runs Python 3.14. For a new environment, install the listed packages. The generated source register and request sidecars record URLs, filters, retrieval dates and original SHA-256 digests.

## Acquisition provenance

The earlier ten-year acquisition fetched 2015–2025 crime; the active study uses only 2022–2025 plus NYC current-feed late reports of those occurrences. These earlier unused raw partitions remain preserved and labeled. Thirty-three original source partitions plus four NYC late-report partitions are reconciled. NYC historic/current scopes are robbery and burglary; Buffalo includes all published crime types; Rochester includes all Part I categories.

Acquisition scripts are resumable and preserve hashed cached responses. `acquire.py` initially acquired the broader ten-year corpus; running it now checks cached files and late-report supplementation. `prepare_inputs.py` was used once to copy and verify older official ATM/boundary downloads with provenance. Offline rebuilds do not require any earlier restart directory. `acquire_atm.py` recovered indexed February–November 2023 archives; its export-preparation requests create public download copies, not source edits. Source-discovery failures are retained as evidence, not ingested data. A fresh source vintage should go in a separate release rather than overwrite this one.

## Main files

- data/processed/atm_panel_full_year_2024_2025.csv — primary full-year cohorts, 366/365 supported days.
- data/processed/atm_panel_partial_2023.csv — separate 313-day address-continuity cohort.
- data/processed/atm_panel_continuity_2023_2025.csv — convenience union of the two above, with duration and cohort columns.
- data/processed/atm_panel_exact_supported_2023_2025.csv — alternative exact-identity interval sensitivity; do not stack with the continuity panel.
- data/processed/event_atm_links.csv.part001–part004 — tracked byte parts of all cohort-specific outcome/background links; restore the exact CSV using the command above. Counts include overlap between alternative cohorts.
- data/processed/qa/exact_exposure_intervals.csv — authoritative supported-day union for exact identity.
- data/processed/atm_site_month_panel.csv — supported monthly exposure/outcome subdivisions, reconciled to annual rows; no repeated annual baseline predictors.
- data/processed/crime_primary_2022_2025.csv — deduplicated geocoded robbery/burglary, with source references.
- data/processed/qa/ — attrition, exclusions, source conflicts, sensitivity tables and independent-review work queues.
- reports/validation.json — independent computational checks.
- reports/phase_status.json — computational completion and pending scientific gates.

The static map is self-contained and works offline. Figures are supplied as PNG and SVG. They describe data and sensitivity; they are not prediction or causal results.
''')
 status={'release':'restart5_0','scope':'maximum_recovered_continuous_monthly_ATM_snapshots','user_superseded_ten_year_request':True,'snapshot_start':'2023-02-22','snapshot_end':'2026-01-15','full_years':[2024,2025],'partial_2023_supported_days':313,'phase_1':{'computational_status':'COMPLETE','scientific_approval':'PENDING'},'phase_2':{'computational_status':'COMPLETE','validation':'PASS','full_year_site_years':len(full),'partial_2023_site_periods':len(early),'exact_identity_sensitivity_rows':len(exact),'scientific_approval':'PENDING'},'phases_3_to_5':'NOT_STARTED_NOT_REQUESTED','confirmatory_eligible':False,'review_gates':[g['gate'] for g in gates]}
 savejson(REPORTS/'phase_status.json',status)
 (ROOT/'README.md').write_text(f'''# Restart 5.0 — phases 1 and 2 complete

Computational work and independent automated validation are complete for the user's revised scope: the longest recovered continuous ATM snapshot period. Scientific approval remains pending.

- **Monthly snapshots:** 22 February 2023–15 January 2026 (36 snapshots).
- **Complete outcome years:** 2024–2025, **{len(full):,} site-years**.
- **Partial 2023:** 22 February–31 December (313 days), **{len(early):,} site-periods**.
- **Crime inputs analyzed:** 2022–2025, including NYC late reports from the current-year feed; 2022 is background-only.
- **No models fitted.** Nearby robbery/burglary is not verified ATM-targeted crime.

The ten-year plan was superseded at the user's request. Its raw downloads and protocol remain preserved. The first incomplete year is explicitly partial; contemporary ATMs are never backcast into unsupported years.

[Full execution report](reports/phase_1_2_report.md) · [Methods](reports/methods.md) · [Quality and sensitivities](reports/quality_and_sensitivity.md) · [Lessons applied](reports/lessons_from_previous_attempts.md) · [Offline map](reports/atm_locations_map.html) · [Reproduce](reports/reproduce.md)

[Full-year panel](data/processed/atm_panel_full_year_2024_2025.csv) · [Partial 2023 panel](data/processed/atm_panel_partial_2023.csv) · [Combined continuity panel](data/processed/atm_panel_continuity_2023_2025.csv) · [Exact-identity sensitivity](data/processed/atm_panel_exact_supported_2023_2025.csv) · [Data dictionary](data/processed/data_dictionary.csv) · [Validation](reports/validation.json) · [Phase status](reports/phase_status.json)

The large event-link CSV is stored in four tracked parts (`data/processed/event_atm_links.csv.part001` through `.part004`). The offline rebuild recreates and checksum-checks the complete local CSV. To restore it without rebuilding, run `python3 scripts/large_artifacts.py restore restart5_0/data/processed/event_atm_links.csv` from the repository root.

The panels are alternative exposure definitions: do not stack continuity and exact-identity rows. Monthly membership is an assumption about continuity, not observed operation. Buffalo coordinate precision, missing earlier reporting times, facility identity and independent linkage/codebook review remain material limitations. `confirmatory_eligible=false`.

```bash
.venv/bin/python restart5_0/scripts/run_all.py
```
''')
 print('Reports, figures, map, sensitivity tables and status written',flush=True)
if __name__=='__main__':main()
