"""Descriptive Phase 3 QA, standalone plots and reproducible release notes."""
import collections
import json
import os
import numpy as np
from scipy.stats import spearmanr
os.environ.setdefault('MPLCONFIGDIR','/tmp/atmsop2-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from phase3_common import *

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+[
        '| '+' | '.join(str(v) for v in row)+' |' for row in rows])

def main():
    validation=json.loads((OUT/'qa/validation.json').read_text());assert validation['status']=='PASS'
    defs=definitions();lookup={r['row_id']:r for r in read(OUT/'data/site_lookup_and_quality.csv')}
    units={'population_density':'persons per km2 land','median_household_income':'2022 USD',
        'median_gross_rent':'2022 USD per month','housing_age':'years relative to 2022',
        'employment_density':'jobs per unprotected acre','retail_employment_density':'retail jobs per unprotected acre',
        'employment_mix':'fixed-five-category entropy, 0 to 1','road_network_density':'facility miles per square mile land',
        'auto_road_density':'auto-oriented facility miles per square mile land',
        'intersection_density':'weighted pedestrian intersections per square mile',
        'transit_service_density':'evening-peak departures per hour per square mile',
        'auto_job_accessibility':'travel-time-weighted accessible jobs','transit_job_accessibility':'transit-accessible jobs',
        'transit_centroid_distance':'metres from block-group population centroid',
        'atm_density_500m':'other mapped ATM objects per km2 circle','nearest_other_atm':'metres'}
    dictionary=read(OUT/'data/feature_dictionary.csv')
    for r in dictionary:
        r['raw_unit']=units.get(r['name'],'fraction' if r['source']=='ACS2022' else 'incidents')
        r['spatial_support']='block group' if r['source'] in ('ACS2022','EPA_SLD2021') else 'prior-December mapped-object neighborhood' if r['source']=='prior_December_OSM' else 'site-centred geodesic radius or annulus'
    write(OUT/'data/feature_dictionary.csv',dictionary)
    models={k:{} for k in lookup}
    for role in ('primary','sensitivity'):
        for suffix in ('full_year_2024_2025','partial_2023'):
            for r in read(OUT/f'data/features_{role}_{suffix}.csv'):
                models[r['row_id']].update({k:number(v) for k,v in r.items() if k!='row_id'})
    distributions=[];correlations=[];join_summary=[]
    names=[f['predictor'] for f in defs if f['role']=='primary']
    for year in ('2023','2024','2025','ALL'):
        for city in [*CITIES,'ALL']:
            ids=[k for k,q in lookup.items() if (year=='ALL' or q['outcome_year']==year) and (city=='ALL' or q['city']==city)]
            for f in defs:
                name=f['predictor'];values=[models[k][name] for k in ids if models[k][name] is not None]
                q=np.quantile(values,[0,.25,.5,.75,1]).tolist() if values else [None]*5
                missing=len(ids)-len(values)
                distributions.append({'year':year,'city':city,'feature':name,'role':f['role'],'rows':len(ids),
                    'missing':missing,'missing_fraction':missing/len(ids),'min':q[0],'q25':q[1],'median':q[2],'q75':q[3],'max':q[4],
                    'high_missingness_gt20pct':missing>.2*len(ids),'zero_variance_or_all_missing':len(set(values))<=1})
            for i,a in enumerate(names):
                for b in names[i+1:]:
                    pairs=np.array([[models[k][a],models[k][b]] for k in ids if models[k][a] is not None and models[k][b] is not None])
                    rho=None
                    if len(pairs)>=3 and np.ptp(pairs[:,0])>0 and np.ptp(pairs[:,1])>0:rho=float(spearmanr(pairs[:,0],pairs[:,1]).statistic)
                    correlations.append({'year':year,'city':city,'feature_a':a,'feature_b':b,'pairwise_n':len(pairs),
                        'spearman_rho':rho,'abs_rho_ge_0_90':rho is not None and abs(rho)>=.9})
            if year!='ALL' and city!='ALL':
                join_summary.append({'city':city,'year':year,'site_years':len(ids),
                    'acs_unique':sum(lookup[k]['acs_matches']=='1' for k in ids),
                    'sld_unique':sum(lookup[k]['sld_matches']=='1' for k in ids),
                    'atm_density_covered':sum(lookup[k]['atm_density_coverage']=='True' for k in ids),
                    'atm_nearest_covered':sum(lookup[k]['atm_nearest_coverage']=='True' for k in ids),
                    'report_filtered_crime_available':sum(lookup[k]['report_filtered_crime_available']=='True' for k in ids)})
    write(OUT/'qa/feature_distributions.csv',distributions);write(OUT/'qa/feature_correlations.csv',correlations)
    write(OUT/'qa/join_and_availability_summary.csv',join_summary)
    plots=OUT/'figures';plots.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':9,'figure.dpi':160,'savefig.bbox':'tight'})
    columns=[(city,year) for city in CITIES for year in ('2024','2025')]
    matrix=np.array([[next(r['missing_fraction'] for r in distributions if (r['city'],r['year'],r['feature'])==(city,year,name)) for city,year in columns] for name in names])
    fig,ax=plt.subplots(figsize=(8,10));im=ax.imshow(matrix,vmin=0,vmax=1,cmap='YlOrRd',aspect='auto')
    ax.set_yticks(range(len(names)),[n.replace('log1p_','').replace('_',' ') for n in names])
    ax.set_xticks(range(len(columns)),[f'{CITIES[city].upper()}\n{year}' for city,year in columns])
    ax.set_title('Primary-feature missingness by city and year')
    fig.colorbar(im,ax=ax,label='Fraction missing',shrink=.5);fig.tight_layout()
    fig.savefig(plots/'primary_missingness.png');fig.savefig(plots/'primary_missingness.pdf');plt.close(fig)
    show=['log1p_population_density','housing_vacancy_share','log1p_atm_density_500m']
    fig,axes=plt.subplots(1,3,figsize=(12,3.8))
    for ax,name in zip(axes,show):
        vals=[[models[k][name] for k,q in lookup.items() if q['city']==city and q['outcome_year']=='2024' and models[k][name] is not None] for city in CITIES]
        ax.boxplot(vals,tick_labels=['NYC','Chicago','LA'],showfliers=False)
        ax.set_title(name.replace('log1p_','log(1 + ') .replace('_',' ')+(')' if name.startswith('log1p_') else ''))
        ax.grid(axis='y',alpha=.2)
    fig.suptitle('2024 descriptive feature distributions; no outcome comparison')
    fig.tight_layout();fig.savefig(plots/'feature_distributions_2024.png');fig.savefig(plots/'feature_distributions_2024.pdf');plt.close(fig)
    sources=[
        {'source':'ACS 2018–2022 five-year summary files','vintage':'2022; released 2023-12-07',
         'url':'https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/data/5YRData/',
         'use':'11 population/economic/housing predictors','limitation':'Fixed pre-2024 context; API-only non-jam annotations unavailable; no 2023 predictors'},
        {'source':'2022 TIGER/Line block groups','vintage':'2022','url':'https://www2.census.gov/geo/tiger/TIGER2022/BG/',
         'use':'ACS spatial joins and official land area','limitation':'Polygon context is not a 50 m ATM buffer'},
        {'source':'EPA Smart Location Database v3','vintage':'2021 release; 2019 block-group geometry',
         'url':'https://www.epa.gov/smartgrowth/smart-location-mapping','use':'8 primary and 2 sensitivity measures',
         'limitation':'Older mixed-year measurements; centroid transit distance is not ATM-to-transit distance'},
        {'source':'Historical OSM via HeiGIT','vintage':'2023-12-15 and 2024-12-15',
         'url':'https://www.openstreetmap.org/copyright','use':'Mapped ATM competition from verified Phase 2 raw snapshots',
         'limitation':'ODbL; mapped objects are not a complete inventory or verified distinct facilities'},
        {'source':'Restart 6 harmonized police records','vintage':'2022–2024 occurrences used as predictors',
         'url':'../../../reports/phase_1_2_report.md','use':'Prior-crime candidates and annulus background',
         'limitation':'Latest extracts; Chicago original report dates unavailable; LA reporting-system break; block geocodes'},
    ]
    write(OUT/'data/source_register.csv',sources)
    summary=table(['City','Year','Site-years','Unique ACS joins','Unique EPA joins','ATM-density coverage'],[
        [r['city'],r['year'],r['site_years'],r['acs_unique'],r['sld_unique'],r['atm_density_covered']] for r in join_summary])
    mainflags=[r for r in distributions if r['year'] in ('2024','2025') and r['city']!='ALL' and r['role']=='primary' and r['high_missingness_gt20pct']]
    flags=table(['City','Year','Feature','Missing / rows'],[[r['city'],r['year'],r['feature'],f"{r['missing']} / {r['rows']}"] for r in mainflags])
    highcorr=[r for r in correlations if r['year'] in ('2024','2025') and r['city']!='ALL' and r['abs_rho_ge_0_90']]
    invalid_rows=sum(bool(q['sld_invalid_source_geoids'] or q['acs_invalid_source_geoids']) for q in lookup.values())
    (OUT/'docs').mkdir(parents=True,exist_ok=True)
    (OUT/'docs/01_work_completed.md').write_text(f'''# Phase 3 work completed

Built and validated features for all 2,731 main site-years and 1,287 separately labeled partial-2023 site-periods. The three cities are New York City, Chicago and Los Angeles city. The phases 1–2 files remain unchanged and their hashes were verified.

Reused the frozen Restart 4 feature families and the national housing tables already downloaded for Restart 3. Retrieved the missing population/economic tables, California/Illinois TIGER geometry and EPA county polygons. New and reused inputs have individual hashes and original retrieval sidecars in `qa/input_manifest.csv`. Cook and DuPage counties cover Chicago; Los Angeles uses county 037; NYC uses its five borough counties.

Replaced DFS competition measures with prior-December OSM objects matching Restart 6's population. Reconstructed six nearby prior-crime candidates from source incidents; retained both report-filtered and explicitly retrospective unfiltered versions. No models, imputation, scaling, target-based feature selection or row dropping were performed.

{len(validation['checks'])} validation groups passed, with {validation['acs_source_cells_verified']:,} ACS source cells checked, all {validation['prior_event_links']:,} prior-event links replayed, {validation['bruteforce_sampled_site_years']} direct spatial omission checks, and all 2,731 main ATM-competition rows reconstructed. Four synthetic regression tests cover missingness, invalid polygons, source boundaries and report/year cutoffs.
''')
    (OUT/'docs/02_methods.md').write_text('''# Phase 3 methods

The [frozen specification](../../../protocol/phase3_feature_spec.md) and [machine-readable formulas](../../../protocol/phase3_variables.json) define 28 primary predictors: one annulus baseline, 21 environmental/housing/ATM candidates and six nearby prior-crime candidates. Nine sensitivity predictors include two EPA transit measures and seven unfiltered crime measures. Primary and sensitivity matrices have only the row key and allowlisted predictors. Labels and site metadata are separate.

ACS 2018–2022 estimates were released on December 7, 2023. Use that fixed vintage for 2024–2025 and leave ACS predictors unavailable in partial 2023. Join to 2022 TIGER block groups with official ALAND. Population density is persons per km² of land; income/rent are nominal 2022 dollars. Housing age is 2022 minus median construction year. Shares follow the saved numerator/denominator definitions. Estimates, margins of error, source sentinel values and jam annotations are retained. Other API-only annotations are unavailable from bulk files. No ratio margins of error are inferred.

EPA SLD v3 uses 2019 block-group geography and measurements from mixed earlier years. Join it separately from ACS with polygon covers. Ambiguous or unmatched joins remain missing. Geometry repairs are audited. The [geometry exception](../../../protocol/phase3_geometry_policy.md) excludes an invalid Chicago polygon from joins and masks its bounding rectangle conservatively; it does not relax the repair tolerance. EPA road and transit variables describe neighborhood context, not exact site security or ATM-to-road/transit distances.

ATM competition uses every valid raw OSM object in the prior-December query bounding box, including points outside the municipality. Exclude only the focal type/ID; retain other co-located objects for review. Non-points use projected centroids. Density divides the geodesic 500 m count by pi × 0.5² km². Coverage must reach the full 500 m circle; nearest-neighbor distance must be inside the conservative query margin. Missing December 2022 inventory leaves competition missing in the 2023 supplement. This is mapped-object competition and may include duplicate physical facilities. No later-survival filter is used.

Crime predictors use only the preceding calendar year at WGS84 distances <=25/50/100 m, robbery/burglary separately <=50 m, and July–December <=50 m. Report-filtered counts require a usable report date strictly before January 1. Chicago's missing original report dates leave all seven primary crime variables blank, including at sites with no matching observed events. Unfiltered sensitivity variables are retrospective context. NYC/LA late or unusable reports are recorded separately. The annulus baseline is inherited unchanged from Phase 2.

Natural log1p transforms and ratios are deterministic. Missingness, zero variance and correlations are diagnostics, not exclusion rules. Future imputation, scaling and selection must occur within training folds. Neither outcome year is a pristine holdout from all previous study decisions. Cohort membership and baseline locations remain retrospective.

Official source documentation: [ACS release schedule](https://www.census.gov/programs-surveys/acs/news/updates/2023.html), [ACS public summary files](https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/), [TIGER 2022](https://www2.census.gov/geo/tiger/TIGER2022/BG/), [EPA SLD](https://www.epa.gov/smartgrowth/smart-location-mapping). OSM data © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright), via HeiGIT ohsome.
''')
    (OUT/'docs/03_results.md').write_text(f'''# Phase 3 descriptive results

Computational build and automated validation passed. These are feature-construction results, not evidence of predictive improvement or a causal environmental effect. Scientific review remains pending.

{summary}

## Missingness exceeding 20% in a main city/year

{flags}

Chicago's seven report-filtered crime variables are unavailable by design. Partial 2023 additionally lacks all 11 ACS and both ATM-competition predictors at its cutoff; it is a separate limited supplement. Other blanks retain their source or join meaning. No missing values were replaced by zero or globally imputed.

There are {len(highcorr)} main city/year feature-pair flags with absolute Spearman correlation >=0.90. Both concern Los Angeles's prior full-year and July–December crime counts within 50 m (2024 rho 0.957; 2025 rho 0.903). No predictors were dropped on this basis. See [all correlations](../qa/feature_correlations.csv), [distributions](../qa/feature_distributions.csv) and [join/availability summary](../qa/join_and_availability_summary.csv).

The invalid-source-geometry policy affects {invalid_rows} cohort rows. See [geometry diagnostics](../qa/geometry_repairs.csv) and [per-row joins](../qa/spatial_join_audit.csv); unusable geometry is not accepted as a repaired source polygon.

![Main-feature missingness](../figures/primary_missingness.png)

![Descriptive distributions](../figures/feature_distributions_2024.png)

The OSM sampling/identity limitations, public block crime coordinates, LA source transition, unavailable Chicago report dates and fixed old context vintages remain material. A three-city model must explicitly address Chicago's absent primary baseline rather than treating its unknown availability as zero. Phase 4 was not executed.
''')
    (OUT/'docs/04_reproduce.md').write_text('''# Reproduce Phase 3

From the repository root:

```bash
.venv/bin/python restart6_0/scripts/run_phase3.py
```

This performs an offline rebuild, checks frozen Phase 1–2 and Phase 3 inputs, runs the four synthetic regression tests, builds features, validates sources/formulas/links, renders diagnostics and writes manifests. It does not require the HeiGIT key. Dependencies are in `restart6_0/phase3/requirements.txt`; the existing environment already contains them.

For first-time public acquisition, run:

```bash
.venv/bin/python restart6_0/scripts/run_phase3.py --acquire
```

New raw inputs are under `restart6_0/phase3/raw`. Reused national ACS housing tables and NYC geography remain at their original repository paths, explicitly listed in `qa/input_manifest.csv`; those inputs must accompany this release for offline reproduction. If the ignored Phase 2 large CSVs are absent after checkout, first run `.venv/bin/python restart6_0/scripts/large_artifacts.py restore`.

Main matrices are `data/features_primary_full_year_2024_2025.csv` and `data/features_sensitivity_full_year_2024_2025.csv`. Separate year files and partial-2023 supplements are included. Join by `row_id` to `data/outcomes.csv` and `data/site_lookup_and_quality.csv`. Never feed lookup flags, labels, future exposure or sensitivity columns into a model by selecting all numeric columns. Use `data/feature_schema.json` and learn any preprocessing within training folds.

`qa/phase3_status.json` is the authoritative Phase 3 status. The original Phase 1–2 status and manifest stay frozen. `qa/output_manifest.csv` includes result files, scripts and tests; `qa/input_manifest.csv` includes raw/reused inputs and protocol hashes. These checks establish computational integrity, not independent scientific approval.
''')
    (OUT/'README.md').write_text(f'''# Restart 6 — Phase 3

**Computationally complete and validated.** Scientific review remains pending; no models were fitted.

Built **2,731 main site-years** (2024–2025) with **28 primary and 9 sensitivity predictors**, plus a separate **1,287-row partial-2023 supplement**. All {len(validation['checks'])} validation groups and four synthetic regression tests passed. Phase 1–2 artifacts are unchanged.

{summary}

Chicago's report-filtered crime predictors stay missing because original report dates are unavailable. Partial 2023 lacks pre-cutoff ACS 2022 and December 2022 ATM competition. Missingness is explicit; there was no imputation or row dropping. `confirmatory_modeling_ready=false`.

[Work completed](docs/01_work_completed.md) · [Methods](docs/02_methods.md) · [Results](docs/03_results.md) · [Reproduce](docs/04_reproduce.md) · [Validation](qa/validation.json)

[Main feature matrix](data/features_primary_full_year_2024_2025.csv) · [Sensitivity matrix](data/features_sensitivity_full_year_2024_2025.csv) · [Schema](data/feature_schema.json) · [Dictionary](data/feature_dictionary.csv) · [Lookup and quality](data/site_lookup_and_quality.csv) · [Source register](data/source_register.csv)

```bash
.venv/bin/python restart6_0/scripts/run_phase3.py
```

OSM data © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright), via HeiGIT ohsome. Other inputs: US Census Bureau and EPA.
''')
    print('Phase 3 reports, diagnostics and standalone figures written',flush=True)

if __name__=='__main__':main()
