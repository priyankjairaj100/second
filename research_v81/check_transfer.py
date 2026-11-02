"""Bounded generated archive/service qualification only, no empirical data."""
import json,sys,time,unittest
from pathlib import Path
from research_v79.check_integration import LEGACY

def main(output):
    start=time.perf_counter_ns();result=dict(empirical_execution=False,scope='Generated matched-depth archive/service guards only',suites={})
    for name,modules,count in (
        ('legacy',LEGACY,44),('four_cell_integration',['research_v79.test_integration'],5),
        ('profiles',['research_v81.test_profile'],4),('full_geometry_archives',['research_v81.test_archive'],5),
        ('service_guards',['research_v81.test_service'],4)):
        tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
        result['suites'][name]=dict(tests=tests.testsRun,failures=len(tests.failures),errors=len(tests.errors),skipped=len(tests.skipped))
        if not (tests.wasSuccessful() and tests.testsRun==count and not tests.skipped):raise RuntimeError('Exact-count transfer software gate failed: '+name)
    result['elapsed_ns']=time.perf_counter_ns()-start
    Path(output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main(sys.argv[1])
