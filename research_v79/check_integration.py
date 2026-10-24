"""Exact-count Linux integration gate using artificial tiny decoder inputs."""
import json
from pathlib import Path
import sys
import time
import unittest

LEGACY = ['research_v63.test_control', 'research_v63.test_runner',
          'research_v64.test_service', 'research_v64.test_linux',
          'research_v66.test_operations', 'research_v66.test_linux']


def main(output):
    start = time.perf_counter_ns()
    result = dict(scope='Generated tiny service software qualification only; no empirical checkpoint or corpus',
                  empirical_execution=False, suites={})
    for name, modules, expected in [('legacy', LEGACY, 44),
                                   ('four_cell_integration', ['research_v79.test_integration'], 5)]:
        suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
        r = unittest.TextTestRunner(verbosity=2).run(suite)
        result['suites'][name] = dict(tests=r.testsRun, failures=len(r.failures), errors=len(r.errors), skipped=len(r.skipped))
        assert r.wasSuccessful() and r.testsRun == expected and not r.skipped
    result['elapsed_ns'] = time.perf_counter_ns()-start
    Path(output).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main(sys.argv[1])
