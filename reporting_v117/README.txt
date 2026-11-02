V117 is prepared reporting code, not a new experiment or empirical result.

Only after all V112 jobs and both audits have completed successfully, first run
the existing reporting_v113/collect.py once into a new directory. Then run:
python3 -B -m reporting_v117.render COLLECTION_DIRECTORY NEW_REPORT_DIRECTORY

The renderer revalidates the exact actual program and all21job IDs, recomputes the
unchanged V113 saved-metadata reduction and requires complete equality with the
collected reduction. It preserves every cell, endpoint, cost, source access,
negative result and scope limitation. No destination is created before checks pass.
Original registered source files and jobs are never changed or executed.

Generated test fixtures are software evidence only. Do not render partial actual
data or call a pending model comparison successful. Native compilation and review
of any later manuscript edits remain separate requirements. No scheduler is added.
