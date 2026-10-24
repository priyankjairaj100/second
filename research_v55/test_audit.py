"""Tampering and adverse-result fixtures for the additive quality auditor."""
import copy
import math
import unittest
from research_v55 import audit,diagnostic
from research_v55.test_diagnostic import quality
from research_v43.dispatcher import ResourcePolicy
from src.compact_state import StageCodes
from src.run_store import digest


def stages():
    return tuple(StageCodes('stage-'+str(i),1,2,'dyadic_row',4,(),b'\x87',(1.,)) for i in range(24))


def result(delta):
    q=quality(delta);history=dict(quality=quality())
    parity=diagnostic.parity(q,history);summary=diagnostic.summarize(q)
    return dict(status='complete',valid_diagnostic=True,quality=q,historical_parity=parity,
        summary=summary,development_guards_pass=summary['development_guards_pass']),history,parity


class AuditTests(unittest.TestCase):
    def test_sequential_packed_extent_hash_and_matched_grids(self):
        fixed=stages();blob=b''.join(s.packed_indices for s in fixed)
        meta=dict(target_sha256='target',stages=[s.metadata() for s in fixed])
        self.assertEqual(diagnostic.reconstruct_sequential(blob,meta,target_sha256='target',fixed=fixed),fixed)
        variants=[(blob+b'x',meta),(blob[:-1],meta),(b'\x88'+blob[1:],meta)]
        bad=copy.deepcopy(meta);bad['stages'].pop();variants.append((blob,bad))
        bad=copy.deepcopy(meta);bad['stages'][0]['scale_values_hex']=[float(2).hex()];variants.append((blob,bad))
        bad=copy.deepcopy(meta);bad['target_sha256']='wrong';variants.append((blob,bad))
        for data,metadata in variants:
            with self.assertRaises(ValueError):diagnostic.reconstruct_sequential(data,metadata,target_sha256='target',fixed=fixed)

    def test_valid_poor_quality_is_preserved_and_not_reclassified_as_execution_failure(self):
        for delta,expected in ((0.,True),(math.log(1.3),False)):
            c,h,p=result(delta)
            self.assertEqual(diagnostic.check_result(c,h,p)['development_guards_pass'],expected)

    def test_summary_and_parity_mutation_are_rejected(self):
        c,h,p=result(0.)
        for key in ('summary','historical_parity'):
            bad=copy.deepcopy(c);bad[key]={}
            with self.assertRaises(ValueError):diagnostic.check_result(bad,h,p)
        bad=copy.deepcopy(c);bad['quality']['fixed_feature'][0]['nll_sum']+=1
        with self.assertRaises(ValueError):diagnostic.check_result(bad,h,p)
        bad=copy.deepcopy(c);bad['development_guards_pass']=False
        with self.assertRaises(ValueError):diagnostic.check_result(bad,h,p)
        bad=copy.deepcopy(c);bad['quality']['nearest_rounding'][0]['nll_sum']+=1
        with self.assertRaises(ValueError):diagnostic.check_result(bad,h,p)

    def test_prefix_chain_neural_extent_and_resource_admission_bindings(self):
        codes=stages();rows=[];admissions=[]
        for i,s in enumerate(codes):
            rows.append(dict(stage_id=s.stage_id,feature_tokens=768,input_width=s.columns,output_rows=s.rows,
                route='streamed',installed_parent_stage_id=codes[i-1].stage_id if i else None,
                installed_parent_packed_sha256=digest(codes[i-1].packed_indices) if i else None))
            admissions.append(dict(stage_id=s.stage_id,selected_route='streamed',admitted=True,work_units=1,policy=ResourcePolicy().__dict__))
        d=dict(schema='dispatched-sequential-calibration-v55',target_sha256='target',records=6,retained_tokens=768,
            neural_stage_record_pairs=144,prior_model_access=False,prior_factor_access=False,stages=rows,point_admission=admissions)
        audit.check_prefix(d,codes,'target')
        bad=copy.deepcopy(d);bad['stages'][3]['installed_parent_packed_sha256']='wrong'
        with self.assertRaises(ValueError):audit.check_prefix(bad,codes,'target')
        bad=copy.deepcopy(d);bad['neural_stage_record_pairs']=24
        with self.assertRaises(ValueError):audit.check_prefix(bad,codes,'target')
        bad=copy.deepcopy(d);bad['point_admission'][0]['admitted']=False
        with self.assertRaises(ValueError):audit.check_prefix(bad,codes,'target')
        bad=copy.deepcopy(d);bad['point_admission'][0]['work_units']=2_000_000_000_000
        with self.assertRaises(ValueError):audit.check_prefix(bad,codes,'target')


if __name__=='__main__':unittest.main()
