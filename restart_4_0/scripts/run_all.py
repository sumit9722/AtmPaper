"""Offline reproduction of the complete five-phase Restart 4.0 release."""
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    commands=[['build.py'],['run_models.py','--phase','4'],['uncertainty.py','--phase','4'],
              ['validate.py','--phase','4'],['run_models.py','--phase','5'],
              ['uncertainty.py','--phase','5'],['validate.py','--phase','5'],['report.py']]
    for command in commands:
        print('Running',*command,flush=True)
        subprocess.run([sys.executable,str(ROOT/'scripts'/command[0]),*command[1:]],check=True,cwd=ROOT.parent)

if __name__=='__main__':main()
