"""Validate actual endpoint schema before numerical work or source extraction."""
def endpoint(profile,count):
 assert type(count)is int and count in (2,3)
 e=profile['endpoints'];assert set(e)=={'candidate_2','candidate_3'},'Exact registered endpoint keys required'
 for key in e:
  assert set(e[key])=={'completion','model'},'Exact endpoint artifact set required'
  for value in e[key].values():
   assert set(value)=={'path','bytes','sha256'}
   assert isinstance(value['path'],str) and value['path'].startswith('/')
   assert type(value['bytes']) is int and value['bytes']>0
   assert len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256'])
 return e['candidate_'+str(count)]
