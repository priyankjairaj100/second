"""Metadata/shape-only tests; they establish no actual model result."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from research_v81.profile import validate_geometry,validate_records,SHAPES,KINDS

def manifest(blocks):
    return dict(recipe=dict(original_token_count=512,bits=4,ridge=[1,100],max_grid_entries=1_327_104),stages=[
        dict(stage_id=f'block.{i:04d}.{kind}',shape=list(shape),normalization=[512,1],ridge=[1,100],grid_axis='output_row',significant_bits=24)
        for i in range(blocks) for kind,shape in zip(KINDS,SHAPES)])

class Checks(unittest.TestCase):
    def test_exact_complete_profiles_and_code_extents(self):
        for blocks,name,codes in ((6,'distilgpt2',42467328),(12,'gpt2',84934656)):
            m=manifest(blocks);self.assertEqual(validate_geometry(m),name)
            self.assertEqual(sum(s['shape'][0]*s['shape'][1] for s in m['stages']),codes)
    def test_missing_extra_reordered_and_mismatched_profile_refuse(self):
        for stages in (manifest(6)['stages'][:-1],manifest(7)['stages'],list(reversed(manifest(12)['stages']))):
            m=manifest(12);m['stages']=stages
            with self.assertRaises(ValueError):validate_geometry(m)
        with self.assertRaises(ValueError):validate_geometry(manifest(12),'distilgpt2')
    def test_recipe_or_stage_mutation_refuses(self):
        m=manifest(12)
        for field,value in (('original_token_count',1664),('bits',3),('ridge',[1,10]),('max_grid_entries',1_000_000),('max_grid_entries',1_327_105)):
            q=deepcopy(m);q['recipe'][field]=value
            with self.assertRaises(ValueError):validate_geometry(q)
        for field,value in (('shape',[2304,769]),('normalization',[1664,1]),('significant_bits',25)):
            q=deepcopy(m);q['stages'][0][field]=value
            with self.assertRaises(ValueError):validate_geometry(q)
    def test_source_count_length_vocabulary_and_duplicates_refuse(self):
        good=[SimpleNamespace(record_id=str(i),tokens=(7,)*128) for i in range(4)];validate_records(good)
        for bad in ([],good+[SimpleNamespace(record_id='5',tokens=(7,)*128)],good[:1]*2,
                    [SimpleNamespace(record_id='x',tokens=(7,)*127)],
                    [SimpleNamespace(record_id='x',tokens=(50257,)*128)],
                    [SimpleNamespace(record_id='x',tokens=(True,)*128)]):
            with self.assertRaises(ValueError):validate_records(bad)

if __name__=='__main__':unittest.main()
