"""Prepared software-only gate; cannot establish empirical transfer or speed."""
import os,platform,resource,sys,unittest
from pathlib import Path
from research_v80.io import require
from research_v91.software import SUITES as PARENT_SUITES
from research_v92.config import ROOT,RUN
from research_v92.records import writer
SUITES=dict(PARENT_SUITES,
    new_matched_contracts=(['research_v92.test_contracts'],5),
    new_matched_design_storage=(['research_v92.test_design'],5),
    new_matched_host=(['research_v92.test_host','research_v92.test_closure','research_v92.test_submit'],16),
    new_matched_live_loader=(['research_v92.test_linux'],3),
    new_matched_seals=(['research_v92.test_receipts'],2),
    new_matched_file_pipeline=(['research_v92.test_worker'],6),
    new_matched_gate_accounting=(['research_v92.test_gate','research_v92.test_accounting'],7),
    new_complete_chain=(['research_v92.test_chain'],2),
    new_complete_clock_scope=(['research_v92.test_timing'],3))

def validate(result):
    require(result==dict(schema='complete-matched-software-v92',empirical_execution=False,
        suites={n:dict(tests=c,failures=0,errors=0,skipped=0) for n,(_,c) in SUITES.items()}),'Every exact Linux suite must pass')
    return True

def main():
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and os.environ.get('SLURM_JOB_ID','').isdigit()
        and Path(__file__).resolve()==RUN/'research_v92/software.py','Pinned new Slurm software child required')
    resource.setrlimit(resource.RLIMIT_CPU,(300,301))
    import numpy,gmpy2,zstandard
    require(platform.python_version()=='3.12.14' and numpy.__version__=='2.3.5' and gmpy2.version()=='2.3.2'
        and zstandard.__version__=='0.25.0' and zstandard.ZSTD_VERSION==(1,5,7) and zstandard.backend=='cext'
        and Path(zstandard.__file__).resolve()==ROOT/'local_runs/lossless-control-v63-20261016-a/deps/zstandard/__init__.py'
        and platform.machine()=='x86_64','Exact numerical/archive runtime required')
    result=dict(schema='complete-matched-software-v92',empirical_execution=False,suites={})
    for name,(modules,count) in SUITES.items():
        r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
        result['suites'][name]=dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped))
        if not (r.wasSuccessful() and r.testsRun==count and not r.skipped):
            writer().write('software-results.json',result);raise RuntimeError('Exact new software suite failed: '+name)
    validate(result);writer().write('software-results.json',result)

if __name__=='__main__':main()
