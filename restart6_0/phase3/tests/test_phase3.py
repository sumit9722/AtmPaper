"""Synthetic edge cases remain in temporary directories, never research outputs."""
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import build_phase3 as b
from phase3_common import acs_value,GEOD,TRANS
from shapely.geometry import box,Polygon,mapping,Point
from shapely.ops import transform

class Phase3Regression(unittest.TestCase):
    def test_invalid_polygon_masks_other_possible_join(self):
        bad=Polygon([(-74,40.7),(-73.9,40.8),(-74,40.8),(-73.9,40.7),(-74,40.7)])
        good=box(-74.1,40.6,-73.8,40.9)
        layer=b.Layer('fixture',[{'properties':{'GEOID':'bad'},'geometry':mapping(bad)},
                                 {'properties':{'GEOID':'good'},'geometry':mapping(good)}])
        self.assertEqual(layer.join(Point(-73.95,40.75),'New York City'),(None,[],None))
        self.assertEqual(layer.invalid_at(Point(-73.95,40.75)),['bad'])
        self.assertEqual(layer.join(Point(-74.05,40.65),'New York City')[0]['GEOID'],'good')

    def test_acs_missingness_and_ratios(self):
        f={'name':'share','components':['N','D'],'numerator':['N'],'denominator':'D'}
        self.assertIsNone(acs_value(f,{'NE':'0','DE':'0'},None))
        self.assertIsNone(acs_value(f,{'NE':'-666666666','DE':'10'},None))
        self.assertEqual(acs_value(f,{'NE':'0','DE':'10'},None),0)
        self.assertEqual(acs_value(f,{'NE':'3','DE':'10'},None),.3)
        age={'name':'age','components':['A'],'subtract_from':2022}
        self.assertIsNone(acs_value(age,{'AE':'2023'},None))
        self.assertEqual(acs_value(age,{'AE':'2022'},None),0)

    def test_atm_focal_exclusion_and_edge_coverage(self):
        city='New York City';lon,lat=-73.99,40.75
        p={'row_id':'fixture','osm_id':'node/1','city':city,'outcome_year':'2024','longitude':lon,'latitude':lat}
        objects={'node/1':(lon,lat),'node/2':GEOD.fwd(lon,lat,90,30)[:2],'node/3':GEOD.fwd(lon,lat,90,400)[:2]}
        region=transform(TRANS[city].transform,box(lon-.1,lat-.1,lon+.1,lat+.1))
        value,links=b.competition(p,(objects,region))
        self.assertAlmostEqual(value['atm_density_500m'],2/(math.pi*.25));self.assertAlmostEqual(value['nearest_other_atm'],30)
        self.assertNotIn('node/1',[l['neighbor_osm_id'] for l in links])
        edge=transform(TRANS[city].transform,box(lon-.001,lat-.001,lon+.001,lat+.001))
        value,_=b.competition(p,(objects,edge));self.assertIsNone(value['atm_density_500m'])
        value,links=b.competition(p,None);self.assertIsNone(value['nearest_other_atm']);self.assertEqual(links,[])

    def test_prior_year_and_report_cutoff(self):
        panels=[];events=[]
        for city,lon,lat in [('New York City',-73.99,40.75),('Chicago',-87.63,41.88),('Los Angeles',-118.25,34.05)]:
            panels.append({'row_id':city,'city':city,'outcome_year':'2024','longitude':lon,'latitude':lat})
            for index,(year,date,report,usable,distance) in enumerate([
                ('2023','2023-06-01','2023-12-31',True,20),
                ('2023','2023-07-01','2024-01-01',True,40),
                ('2023','2023-08-01','',False,80),
                ('2024','2024-01-01','2024-01-01',True,10)]):
                lo,la,_=GEOD.fwd(lon,lat,0,distance)
                events.append({'city':city,'event_id':f'{city}:{index}','event_year':year,'event_date':date,
                    'report_date':report if city!='Chicago' else '',
                    'report_date_usable':str(usable and city!='Chicago'),'category':'robbery','longitude':lo,'latitude':la})
        with tempfile.TemporaryDirectory(prefix='restart6-phase3-test-') as folder:
            with patch.object(b,'OUT',Path(folder)),patch.object(b,'read',return_value=events):results=b.lag_features(panels)
        for city,row in results.items():
            self.assertEqual([row[n+'_unfiltered'] for n in b.LAGS],[1,2,3,2,0,1])
            if city=='Chicago':self.assertTrue(all(row[n] is None for n in b.LAGS))
            else:self.assertEqual([row[n] for n in b.LAGS],[1,1,1,1,0,0])

if __name__=='__main__':unittest.main()
