"""Software fixtures verify service contracts; these are not research data."""
import unittest
from fractions import Fraction as Q
from src.certified_transformer import CertifiedDecoder
from src.row_target_manifest import build_row_target
from src.target_manifest import build_target,TargetRecipe
from src.compact_state import serialize,parse
from src.compact_service import CompactIdentityService,model_digest
from tests.test_transformer_backend import decoder_fixture


class CompactServiceTests(unittest.TestCase):
    def service(self,row=True):
        decoder=CertifiedDecoder(decoder_fixture(block_count=2),primitive_backend='mpfr_enclosure')
        recipe=TargetRecipe(original_token_count=6,bits=3,group_count=1,ridge=Q(1,10))
        target=build_row_target(decoder,recipe) if row else build_target(decoder,recipe,weight_digest_encoding='binary64_matrix_v1')
        return CompactIdentityService(decoder,target)

    def test_four_methods_and_canonical_sequence(self):
        records=[{'id':'a','tokens':[0,1]},{'id':'b','tokens':[2,1]},{'id':'c','tokens':[0,2]}]
        for row in (True,False):
            service=self.service(row)
            original=service.run(records)
            saved=serialize(original.state)
            previous=parse(saved)
            retained=records[1:]
            repaired=service.run(retained,method='repair',prior=previous,deleted_ids=['a'])
            indexed=service.run(retained,method='indexed_fresh',prior=previous,deleted_ids=['a'])
            direct=service.run(retained,method='direct_fresh')
            only=service.run(retained,method='model_only_fresh')
            self.assertEqual(serialize(repaired.state),serialize(direct.state))
            self.assertEqual(serialize(indexed.state),serialize(direct.state))
            self.assertEqual(model_digest(only.stages),model_digest(direct.stages))
            self.assertEqual(serialize(original.state),saved)
            self.assertIsNone(only.state)
            sequential=service.run(records[2:],method='repair',prior=repaired.state,deleted_ids=['b'])
            combined=service.run(records[2:],method='repair',prior=previous,deleted_ids=['a','b'])
            self.assertEqual(serialize(sequential.state),serialize(combined.state))
            empty=service.run([],method='repair',prior=sequential.state,deleted_ids=['c'])
            self.assertEqual(serialize(empty.state),serialize(service.run([]).state))
            self.assertEqual(empty.diagnostics['neural_stage_record_pairs'],0)
            noop=service.run(records,method='repair',prior=previous)
            self.assertEqual(serialize(noop.state),saved)
            self.assertEqual(noop.diagnostics['neural_stage_record_pairs'],0)
            self.assertEqual(noop.diagnostics['changed_ancestor_pairs_avoided'],0)

    def test_batched_solver_preserves_complete_state(self):
        records=[{'id':'a','tokens':[0,1]},{'id':'b','tokens':[2,1]}]
        for row in (True,False):
            reference=self.service(row)
            batched=CompactIdentityService(reference.decoder,reference.target,solver_backend='batched')
            original=reference.run(records).state
            self.assertEqual(serialize(original),serialize(batched.run(records).state))
            expected=reference.run(records[1:]).state
            repaired=batched.run(records[1:],method='repair',prior=original,deleted_ids=['a'])
            self.assertEqual(serialize(expected),serialize(repaired.state))

    def test_membership_and_token_changes_rejected(self):
        service=self.service();records=[{'id':'a','tokens':[0,1]}]
        state=service.run(records).state
        for retained,deletions in [([],[]),(records,['missing']),(records,['a']),([{'id':'a','tokens':[1,0]}],[])]:
            with self.assertRaises(ValueError):service.run(retained,method='repair',prior=state,deleted_ids=deletions)
        with self.assertRaises(ValueError):service.run(records*2)
        with self.assertRaises(ValueError):self.service(False).run(records,method='repair',prior=state)


if __name__=='__main__':unittest.main()
