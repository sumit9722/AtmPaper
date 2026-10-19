import json
import phase3_common as c
R=c.ROOT;O=c.OUT

def main():
 assert json.loads((O/'qa/validation.json').read_text())['status']=='PASS'
 stats=[r for r in c.read(O/'qa/feature_distributions.csv') if r['year']=='ALL' and r['city']=='ALL']
 text='# Housing-context construction\n\n1. Rebuild annual cohorts and labels from the preserved archives.\n2. Freeze eight housing-context definitions before fitting, with prior-year crime as the ninth predictor.\n3. Retrieve official ACS 2018–2022 estimates, margins of error and annotations for seven New York counties; retain raw responses and SHA-256 request records.\n4. Join site points to 2022 block-group polygons using unique covers matches only.\n5. Calculate proportions and fixed-vintage building age; retain missing values and use log1p only for rent, age and crime.\n6. Independently verify every source component and formula, all baseline values and a stratified sample of brute-force spatial joins.\n7. Release the unscaled, unimputed matrices for training-fold preprocessing.\n\nValidation: PASS. This is an exploratory follow-up to already inspected outcomes. Neighborhood estimates do not measure ATM security directly. ACS margins of error are retained but measurement error is not propagated through the predictive models.\n\n| Predictor | Rows | Missing |\n|---|---:|---:|\n'
 for r in stats:text+=f"| {r['feature']} | {r['rows']} | {r['missing']} |\n"
 text+='\nDefinitions: ../../protocol/environment_variables.json. Official source: https://api.census.gov/data/2022/acs/acs5/groups.html\n'
 (O/'docs').mkdir(exist_ok=True);(O/'docs/execution.md').write_text(text)
 c.save(O/'qa/phase3_status.json',dict(build_status='complete',validation_status='PASS',primary_predictors=9,site_years=2442,confirmatory_modeling_ready=False))
 paths=[p for p in O.rglob('*') if p.is_file() and p.name!='output_manifest.csv'];c.write(O/'qa/output_manifest.csv',[dict(file=str(p.relative_to(O)),sha256=c.digest(p),bytes=p.stat().st_size) for p in sorted(paths)])
 print('Housing feature documentation and manifest written.')
if __name__=='__main__':main()
