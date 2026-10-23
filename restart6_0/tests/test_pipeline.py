"""Synthetic regression: missing snapshots, movement, partial-year leakage and null reports.

Fixtures exist only in a temporary directory and never enter research outputs.
"""
import csv
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import Geod, Transformer
from shapely.geometry import Point, box, mapping

RELEASE=Path(__file__).resolve().parents[1]
GEOD=Geod(ellps='WGS84')

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def read_csv(path):
    with path.open() as stream:return list(csv.DictReader(stream))

class PipelineRegression(unittest.TestCase):
    def test_exposure_and_temporal_linkage(self):
        with tempfile.TemporaryDirectory(prefix='restart6-regression-') as folder:
            root=Path(folder)/'restart6_0'
            shutil.copytree(RELEASE/'scripts',root/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'protocol').mkdir();(root/'protocol/study_spec.md').write_text('Synthetic test specification')
            raw=root/'data/raw';out=root/'data/processed';out.mkdir(parents=True)
            dates=json.loads((RELEASE/'data/raw/inherited/snapshot_dates.json').read_text())
            (raw/'osm').mkdir(parents=True);(raw/'osm/snapshot_dates.json').write_text(json.dumps(dates))
            cities={'New York City':('nyc',-73.99,40.75,32618),
                    'Chicago':('chicago',-87.63,41.88,32616),'Los Angeles':('la',-118.25,34.05,32611)}
            boundaries=[];events=[]
            for city,(slug,lon,lat,epsg) in cities.items():
                boundaries.append({'type':'Feature','properties':{'BASENAME':'New York' if slug=='nyc' else city},'geometry':mapping(box(lon-.05,lat-.05,lon+.05,lat+.05))})
                for date in dates:
                    records=[]
                    for oid in (1,2):
                        if city=='Chicago' and oid==2 and date=='2024-06-15':continue
                        distance=0 if oid==1 else 1000
                        if city=='Los Angeles' and oid==2 and date=='2024-06-15':distance+=60
                        x,y,_=GEOD.fwd(lon,lat,90,distance)
                        records.append({'osm_type':'node','osm_id':oid,'tags':[('amenity','atm')],
                            'geom':Point(x,y).wkb,'edit_timestamp':dt.datetime(2020,1,1,tzinfo=dt.timezone.utc),
                            'valid_to_timestamp':dt.datetime(2222,1,1,tzinfo=dt.timezone.utc)})
                    path=raw/f'osm_v2/{slug}/{date}.parquet';path.parent.mkdir(parents=True,exist_ok=True)
                    pq.write_table(pa.Table.from_pylist(records),path)
                    Path(str(path)+'.request.json').write_text(json.dumps({'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'params':{'time':date+'T00:00:00Z'}}))
                trans=Transformer.from_crs(4326,epsg,always_xy=True)
                for year in range(2022,2026):
                    for distance in (20,40,80,250,550):
                        x,y,_=GEOD.fwd(lon,lat,0,distance);east,north=trans.transform(x,y)
                        date=f'{year}-02-21' if year==2023 and distance==20 else f'{year}-03-10'
                        events.append({'city':city,'event_id':f'{slug}:{year}:{distance}','event_year':year,'event_date':date,
                            'report_date':date if city!='Chicago' else '', 'report_date_usable':city!='Chicago',
                            'longitude':x,'latitude':y,'easting_m':east,'northing_m':north,'category':'robbery'})
            (raw/'boundaries').mkdir();(raw/'boundaries/cities.geojson').write_text(json.dumps({'type':'FeatureCollection','features':boundaries}))
            write_csv(out/'crime_primary_2022_2025.csv',events)
            for script in ('build_exposure.py','build_panel.py','build_monthly.py'):
                result=subprocess.run([sys.executable,str(root/'scripts'/script)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            full=read_csv(out/'atm_panel_full_year_2024_2025.csv')
            self.assertEqual(len(full),10)  # 2024: 2+1+1; 2025: 2+2+2
            for city in cities:
                p=next(p for p in full if p['city']==city and p['outcome_year']=='2024' and p['osm_id']=='node/1')
                self.assertEqual([int(p[f'primary_count_{r}m']) for r in (25,50,100)],[1,2,3])
                self.assertEqual(int(p['background_unfiltered_200_500m']),1)
                self.assertEqual(p['background_primary_200_500m'],'' if city=='Chicago' else '1')
                if city=='Chicago':self.assertEqual(p['primary_reported_count_50m'],'')
            early=read_csv(out/'atm_panel_partial_2023.csv')
            for p in early:
                if p['osm_id']=='node/1':
                    self.assertEqual(p['supported_days'],'313')
                    self.assertEqual([int(p[f'primary_count_{r}m']) for r in (25,50,100)],[0,1,2])
            months=read_csv(out/'atm_site_month_panel.csv')
            for p in full+early:
                selected=[m for m in months if m['annual_row_id']==p['row_id']]
                self.assertEqual(sum(int(m['supported_days_in_month']) for m in selected),int(p['supported_days']))
                self.assertEqual(sum(int(m['primary_count_50m']) for m in selected),int(p['primary_count_50m']))

if __name__=='__main__':unittest.main()
