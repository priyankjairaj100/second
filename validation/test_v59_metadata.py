"""Small negative checks for the portable reader, never model execution."""
import importlib.util
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('check_v59_metadata.py')
SPEC = importlib.util.spec_from_file_location('v59_portable_reader', SOURCE)
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)


class MetadataRejections(unittest.TestCase):
    @staticmethod
    def ledger(sources, observed=0, charge=1):
        return dict(schema='phase-cpu-ledger-v1',
            binding=dict(identity=dict(protocol_sha256=reader.PROGRAM_SHA, source_sha256=sources),
                phase_cpu_seconds={'development':14402}, scope='trusted_worker_cpu_admission_not_process_tree_containment'),
            attempts={'example':dict(phase='development',reserved_cpu_seconds=14402,state='settled',
                                    observed_cpu_ns=observed,charged_cpu_seconds=charge)})

    def test_copied_file_tamper_rejected(self):
        with tempfile.TemporaryDirectory(prefix='v59-metadata-fixture-') as temporary:
            root = Path(temporary)
            payload = root/'example.json'
            payload.write_bytes(b'{"status":"original"}')
            manifest = dict(schema='second-terminal-v59-metadata-v1',
                            files={'example.json':reader.file_info(payload)})
            (root/'collection-manifest.json').write_text(json.dumps(manifest))
            checker = reader.Check(root)
            self.assertEqual(checker.collection()['files'], manifest['files'])
            payload.write_bytes(b'{"status":"modified"}')
            with self.assertRaisesRegex(ValueError, 'Copied file hash mismatch'):
                checker.collection()

    def test_valid_adverse_quality_is_not_promoted_to_passing(self):
        quality = {label:[dict(id=rid, predictions=127, nll_sum=127.0*3.0)
                          for rid in reader.IDS] for label in reader.LABELS}
        for row in quality[reader.CANDIDATE]:
            row['nll_sum'] += 127*math.log(1.06)
        summary = reader.summarize(quality)
        self.assertFalse(summary['development_guards_pass'])
        self.assertFalse(summary['guards']['pooled_pass'])
        self.assertTrue(summary['guards']['every_article_pass'])
        self.assertEqual(summary['candidate_comparisons']['sequential']['articles_candidate_higher'],8)

    def test_audit_census_requires_receipts_progress_and_uncopied_binary(self):
        with tempfile.TemporaryDirectory(prefix='v59-audit-fixture-') as temporary:
            root = Path(temporary).resolve()
            campaign = root/reader.CAMPAIGN
            names = ['program.json','registration.json','budget/ledger.json','quality/worker/identity.json',
                     'quality/transaction.json','quality/plan.json','quality/worker/result.json',
                     'quality/outputs/completion.json','quality/worker/attempt-0000/status.json']
            names += [f'quality/outputs/progress-{i:04d}.json' for i in range(69)]
            for name in names:
                path = campaign/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b'{}')
            (root/'fixture.py').write_bytes(b'# fixture\n')
            commitment = reader.byte_info(b'uncopied bytes')
            checker = reader.Check(root)
            checkpoint = reader.REMOTE+'/checkpoint.bin'
            checker.p = dict(inputs={'checkpoint':dict(path=checkpoint,**commitment)}, sources={'fixture.py':'unused here'})
            worker = dict(sealed=dict(attempt='attempt-0000',artifacts={'request.json':commitment,'limits-applied.json':commitment}))
            completion = dict(artifacts={name:dict(file=name,**commitment) for name in reader.ARTIFACTS})
            with patch.object(reader,'REPO',root):
                expected = checker.audit_inputs(worker,completion)
            reader.require_input_inventory(expected,expected)
            mandatory = [reader.DIRECTORY+'/'+name for name in names]
            mandatory += [checkpoint,reader.DIRECTORY+'/quality/outputs/candidate-model.bin',
                          reader.DIRECTORY+'/quality/worker/attempt-0000/request.json']
            for missing in mandatory:
                actual = dict(expected)
                del actual[missing]
                with self.subTest(missing=missing), self.assertRaisesRegex(ValueError,'Audit input census'):
                    reader.require_input_inventory(actual,expected)
            with self.assertRaisesRegex(ValueError,'Audit input census'):
                reader.require_input_inventory({},expected)
            changed = copy.deepcopy(expected)
            changed[checkpoint]['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError,'Audit input commitment'):
                reader.require_input_inventory(changed,expected)

    def test_ledger_requires_full_sources_schema_scope_and_canonical_bytes(self):
        sources = {'src/a.py':'a'*64,'scripts/run_a.py':'b'*64}
        ledger = self.ledger(sources)
        raw = reader.canonical_json(ledger)
        self.assertEqual(reader.validate_ledger(raw,sources),ledger)
        variants = []
        truncated = copy.deepcopy(ledger)
        del truncated['binding']['identity']['source_sha256']['src/a.py']
        variants.append(truncated)
        empty = copy.deepcopy(ledger)
        empty['binding']['identity']['source_sha256'] = {}
        variants.append(empty)
        wrong_schema = copy.deepcopy(ledger); wrong_schema['schema'] = 'other'
        variants.append(wrong_schema)
        wrong_scope = copy.deepcopy(ledger); wrong_scope['binding']['scope'] = 'other'
        variants.append(wrong_scope)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError,'Complete ledger source/schema/scope'):
                reader.validate_ledger(reader.canonical_json(changed),sources)
        with self.assertRaisesRegex(ValueError,'canonical bytes'):
            reader.validate_ledger(raw+b'\n',sources)

    def test_cpu_usage_is_nonnegative_integer_and_zero_charges_one(self):
        sources = {'src/example.py':'a'*64}
        reader.validate_ledger(reader.canonical_json(self.ledger(sources)),sources)
        reader.validate_resource_usage(dict(user_cpu_ns=0,system_cpu_ns=0,total_cpu_ns=0))
        for observed,charge in ((-1,1),(0,0),(True,1),(1.0,1),(1_000_000_001,1)):
            with self.subTest(observed=observed,charge=charge), self.assertRaises(ValueError):
                reader.validate_ledger(reader.canonical_json(self.ledger(sources,observed,charge)),sources)
        for usage in (dict(user_cpu_ns=-1,system_cpu_ns=1,total_cpu_ns=0),
                      dict(user_cpu_ns=True,system_cpu_ns=0,total_cpu_ns=1),
                      dict(user_cpu_ns=0.0,system_cpu_ns=0,total_cpu_ns=0),
                      dict(user_cpu_ns=1,system_cpu_ns=2,total_cpu_ns=4)):
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                reader.validate_resource_usage(usage)

    def test_partial_capture_cannot_be_promoted_by_terminal_looking_files(self):
        with tempfile.TemporaryDirectory(prefix='v59-partial-fixture-') as temporary:
            root = Path(temporary)
            (root/'collection-manifest.json').write_bytes(b'{}')
            checker = reader.Check(root)
            checker.partial_registration_capture = True
            manifest = dict(files={})
            with patch.object(checker,'collection',return_value=manifest), patch.object(checker,'registration',return_value={}), \
                 patch.object(checker,'worker',return_value={'sealed':'terminal looking'}), \
                 patch.object(checker,'terminal',side_effect=AssertionError('partial promoted')):
                result = checker.run()
            self.assertEqual(result['validation_status'],'pending_terminal')
            self.assertFalse(result['cluster_terminal_audit_present'])


if __name__ == '__main__':
    unittest.main()
