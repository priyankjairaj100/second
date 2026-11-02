"""V43 numerical service, with a reviewed thirteen-source Gram admission."""
from research_v35.exact_gram import GramBudget
from research_v43.service import Service as PriorService
from research_v43.service import REPRESENTATIONS, gram_stage, telemetry, trust_json, trust_read


def gram_budget(normalization):
    if normalization!=1664:raise ValueError('V45 requires original normalization1664')
    return GramBudget(max_width=768,max_tokens=1664,max_sources=13,
        max_product_terms=768*769//2*1664,max_integer_bits=256,
        max_serialized_bytes=128*2**20,max_memory_bytes=2*2**30)


class Service(PriorService):
    def __init__(self,checkpoint,normalization,record_provenance,mark=lambda *a,**k:None):
        budget=gram_budget(normalization)
        if len(record_provenance)!=13:raise ValueError('Exactly thirteen registered sources required')
        super().__init__(checkpoint,normalization,record_provenance,mark)
        self.gram_budget=budget
