"""Admission refusal fixtures. No Linux execution, network, model or corpus."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from research_v68 import data_runner as r
from src.run_store import canonical_json,digest


def terminal_values():
    rows=[dict(arm=a,step=s,actual_model_bytes_equal=True,actual_bytes_equal=True,
        code_count=42_467_328,stages=24,source_membership_and_provenance_checked=True,
        independent_retained_traversal_witnessed=True)
        for a in ['cached','cold','hybrid','compressed','modern'] for s in [1,2]]
    primary=dict(status='verified',program_sha256=r.V67_PROGRAM,
        evidence=dict(comparisons=rows),costs={'fixture':1},controllers={'fixture':2})
    supplemental=dict(status='verified',program_sha256=r.V67_PROGRAM,costs=primary['costs'],
        controllers=primary['controllers'],evidence=dict(ten_actual_model_pairs_equal=True,
        primary_receipt_sha256=digest(canonical_json(primary))))
    entries={'v67_'+kind+'_entry':dict(status='complete',error=None,program_sha256=r.V67_PROGRAM,
        operation=kind,job_id=job) for kind,job in [('primary','15274'),('supplemental','15275')]}
    return dict(v67_primary=primary,v67_supplemental=supplemental,**entries)


class DataRunnerTests(unittest.TestCase):
    def test_missing_actual_input_census_refuses_before_any_file_read(self):
        for name in sorted(r.INPUTS):
            with self.subTest(missing=name),patch.object(r,'bound') as read:
                with self.assertRaisesRegex(ValueError,'census'):
                    r.prerequisites(dict(inputs={k:{} for k in r.INPUTS-{name}}))
                read.assert_not_called()

    def test_all_terminal_model_state_membership_and_entry_gates_are_required(self):
        original=terminal_values()
        r.terminal_audits({k:canonical_json(v) for k,v in original.items()})
        mutations=[('v67_primary',('status',),'running'),
            ('v67_primary',('program_sha256',),'0'*64),
            ('v67_primary',('evidence','comparisons',0,'actual_model_bytes_equal'),False),
            ('v67_primary',('evidence','comparisons',0,'actual_bytes_equal'),False),
            ('v67_primary',('evidence','comparisons',0,'code_count'),42),
            ('v67_primary',('evidence','comparisons',0,'stages'),23),
            ('v67_primary',('evidence','comparisons',0,'source_membership_and_provenance_checked'),False),
            ('v67_primary',('evidence','comparisons',0,'independent_retained_traversal_witnessed'),False),
            ('v67_primary',('evidence','comparisons',0,'arm'),'unknown'),
            ('v67_supplemental',('evidence','ten_actual_model_pairs_equal'),False),
            ('v67_supplemental',('evidence','primary_receipt_sha256'),'0'*64),
            ('v67_supplemental',('costs','fixture'),99),
            ('v67_supplemental',('controllers','fixture'),99),
            ('v67_primary_entry',('error',),{'type':'TimeoutError'}),
            ('v67_supplemental_entry',('status',),'failed'),
            ('v67_supplemental_entry',('job_id',),'unrelated')]
        for key,path,value in mutations:
            with self.subTest(key=key,path=path):
                changed=copy.deepcopy(original);target=changed[key]
                for part in path[:-1]:target=target[part]
                target[path[-1]]=value
                if key=='v67_primary':
                    changed['v67_supplemental']['evidence']['primary_receipt_sha256']=digest(canonical_json(changed[key]))
                with self.assertRaises(ValueError):r.terminal_audits({k:canonical_json(v) for k,v in changed.items()})

    def test_history_inventory_excludes_current_run_and_workers_but_refuses_symlinks(self):
        with TemporaryDirectory() as f:
            root=Path(f).resolve();current=root/'local_runs/quality-data-v68-20261016-a'
            for name in ['local_runs/closed/program.json','local_runs/closed/worker/program.json',
                'local_runs/quality-data-v68-20261016-a/registration.json','campaigns/old/selection.json',
                'pilots/old/ignored.json']:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'{}')
            actual=r.history_inventory(root,current)
            self.assertEqual(set(actual),{'local_runs/closed/program.json','campaigns/old/selection.json'})
            (root/'pilots/old/program.json').symlink_to(root/'local_runs/closed/program.json')
            with self.assertRaisesRegex(ValueError,'Regular nonsymbolic'):r.history_inventory(root,current)


if __name__=='__main__':unittest.main()
