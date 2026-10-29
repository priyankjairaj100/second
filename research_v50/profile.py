"""Repeat fixed V49 synthetic cases with only the normal-neighbor backend changed."""
from pathlib import Path
from research_v49.profile import WIDTHS,fixture,run as reference_profile
from research_v50.neighbors import enabled
from research_v43.campaign import read,require


def run(emit):
    root=Path(__file__).resolve().parents[1]
    baseline=read(root/'local_runs/synthetic-profile-v49-20261011-a/outputs/completion.json')
    require(baseline['status']=='complete','Completed baseline profile required')
    expected={r['width']:r for r in baseline['cases']}
    def checked(row):
        if row['phase']=='case_complete':
            old=expected[row['width']]
            for key in ('weights_sha256','features_sha256','code_sha256','rows','tokens'):
                require(row[key]==old[key],'Synthetic baseline commitment differs: '+key)
        emit(row)
    with enabled():return reference_profile(checked)
