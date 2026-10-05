# Revision 11 handoff validation

Date: 5 October 2026.
No research experiment ran during this handoff revision.

Seven metadata-tool tests passed. See `validation/software_tests_v11.txt`.
They check budget preservation, overwrite refusal, bundle hashes, path restrictions, input exclusion, checklist completeness, and size limits.
An actual local initialization captured a runtime contract. The existing verifier accepted it.
A metadata-only review bundle was created successfully.
The reserve-input CLI now requires a new output directory outside archived pilots.
Its help interface and Python syntax were checked. No new dataset preparation ran.

The production `src/` implementation remains unchanged.
The previous 524-test suite and revision 10's ten tests were not rerun together during this handoff.
No new full-model exactness, certificate coverage, quality, or speed evidence exists.
The local empirical program identifies these remaining obligations explicitly.

Pinned requirements reproduce observed top-level versions. They do not lock all transitive dependencies.
Capture the resolved local environment before generating any empirical inventory.
