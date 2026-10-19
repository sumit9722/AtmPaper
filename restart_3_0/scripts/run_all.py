"""Reproduce the independent restart, stopping immediately on any failure."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true',help='Acquire ACS data using CENSUS_API_KEY or hidden prompt, after confirming the credential provider.');parser.add_argument('--download-bulk',action='store_true',help='Acquire the same official ACS vintage from public table-based summary files without an API key.');args=parser.parse_args()
 if args.download and args.download_bulk:parser.error('Choose one acquisition method')
 def run(name,*flags):subprocess.run([sys.executable,str(ROOT/'scripts'/name),*flags],check=True,cwd=ROOT.parent)
 if args.download:run('download_environment.py','--stage','data')
 if args.download_bulk:run('download_environment_bulk.py')
 if not list((ROOT/'data/raw/environment_acs2022/attributes').glob('county_*.json')):
  raise SystemExit('Missing Census housing data. Confirm the key provider, then use --download. No new model results exist yet.')
 for script in ['build.py','validate.py','report.py','build_phase3.py','validate_phase3.py','report_phase3.py','run_phase4.py','validate_phase4.py','report_phase4.py','run_phase5.py','validate_phase5.py','report_phase5.py']:run(script)
if __name__=='__main__':main()
