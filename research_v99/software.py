"""Exact generated-data suites; never a checkpoint transfer result."""
import os,platform,resource,sys,unittest
from research_v79.check_integration import LEGACY
from research_v80.io import require
from research_v99.records import writer
from research_v99.config import RUN,ROOT
from pathlib import Path
SUITES={
 'legacy':(LEGACY,44),
 'four_cell_integration':(['research_v79.test_integration'],5),
 'profiles':(['research_v81.test_profile'],4),
 'full_geometry_archives':(['research_v81.test_archive'],5),
 'service_guards':(['research_v81.test_service'],4),
 'unchanged_input_and_reports':(['research_v82.test_inputs','research_v82.test_admission_reports'],11),
 'bounded_components':(['research_v90.test_metadata','research_v90.test_outputs','research_v90.test_admission',
     'research_v90.test_storage_plan','research_v90.test_recovery_gate'],48),
 'bounded_child_processes':(['research_v90.test_linux'],3),
 'actual_target_wiring':(['research_v99.test_linux'],3),
 'new_host_collector_mapping':(['research_v99.test_host'],8),
 'source_archive_extent':(['research_v99.test_package'],2),
 'saved_host_closure':(['research_v99.test_closure'],4),
 'registry_and_launcher':(['research_v99.test_protocol','research_v99.test_submit'],10),
 'new_admission_contracts':(['research_v99.test_contracts','research_v99.test_storage',
     'research_v99.test_accounting','research_v99.test_fetch'],21),
}


def validate(result):
    require(result==dict(schema='matched-admission-software-v99',empirical_execution=False,
        suites={name:dict(tests=count,failures=0,errors=0,skipped=0) for name,(_,count) in SUITES.items()}),
        'All exact generated software suites must pass without skipped tests')
    return True


def main():
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and os.environ.get('SLURM_JOB_ID','').isdigit(),
        'Pinned Slurm software child required')
    require(Path(__file__).resolve()==RUN/'research_v99/software.py','Literal new software child required')
    resource.setrlimit(resource.RLIMIT_CPU,(300,301))
    import numpy,gmpy2,zstandard
    require(platform.python_version()=='3.12.14' and numpy.__version__=='2.3.5' and gmpy2.version()=='2.3.2'
        and zstandard.__version__=='0.25.0' and zstandard.ZSTD_VERSION==(1,5,7) and zstandard.backend=='cext',
        'Pinned numerical/archive runtime required')
    require(Path(zstandard.__file__).resolve()==ROOT/'local_runs/lossless-control-v63-20261016-a/deps/zstandard/__init__.py'
        and platform.machine()=='x86_64','Actual archive dependency path and CPU architecture required')
    result=dict(schema='matched-admission-software-v99',empirical_execution=False,suites={})
    for name,(modules,count) in SUITES.items():
        suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
        r=unittest.TextTestRunner(verbosity=2).run(suite)
        result['suites'][name]=dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped))
        if not (r.wasSuccessful() and r.testsRun==count and not r.skipped):
            writer().write('software-results.json',result)
            raise RuntimeError('New exact software suite failed: '+name)
    validate(result);writer().write('software-results.json',result)

if __name__=='__main__':main()
