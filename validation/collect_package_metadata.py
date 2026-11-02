"""Bounded public publisher metadata only; no data/model/wheel downloads or installs.

Run explicitly, save stdout to a new report. This records license declarations,
not legal clearance, a complete dependency bill of materials, or scientific data.
"""
import concurrent.futures,datetime,hashlib,json,urllib.request

REQUESTS={
    'distilgpt2':'https://huggingface.co/api/models/distilbert/distilgpt2?blobs=true',
    'c4':'https://huggingface.co/api/datasets/allenai/c4/revision/1588ec454efa1a09f29cd18ddd04fe05fc8653a2',
    **{name:'https://pypi.org/pypi/'+name+'/'+version+'/json' for name,version in [
        ('numpy','2.3.5'),('gmpy2','2.3.2'),('zstandard','0.25.0'),('tokenizers','0.23.2'),
        ('torch','2.10.0'),('safetensors','0.6.2')]}}
MAXIMUM=2*2**20


def collect(item):
    name,url=item;r=dict(url=url,method='GET',metadata_only=True,automatic_retry=False)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Second-metadata-audit/1.0'}),timeout=20) as response:
            raw=response.read(MAXIMUM+1)
            if len(raw)>MAXIMUM:raise ValueError('Metadata response exceeds two MiB')
            r.update(status_code=response.status,final_url=response.url,
                response=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        p=json.loads(raw)
        if name in {'c4','distilgpt2'}:
            card=p.get('cardData') or {}
            r.update(id=p.get('id'),revision=p.get('sha'),license=card.get('license'),
                license_name=card.get('license_name'),license_link=card.get('license_link'),
                private=p.get('private'),gated=p.get('gated'))
            if name=='distilgpt2':
                r['selected_file_metadata']=[v for v in p.get('siblings',[])
                    if v['rfilename'] in {'model.safetensors','config.json','tokenizer.json','README.md','LICENSE','NOTICE'}]
        else:
            i=p['info'];license_text=i.get('license') or ''
            r.update(name=i['name'],version=i['version'],license_expression=i.get('license_expression'),
                license_first_line=license_text.splitlines()[0] if license_text else None,
                license_field_sha256=hashlib.sha256(license_text.encode()).hexdigest(),
                license_classifiers=[v for v in i.get('classifiers',[]) if v.startswith('License ::')],
                project_urls=i.get('project_urls'))
            if name=='safetensors':r.update(installed_or_required_version_verified=False,
                scope_note='Exploratory publisher metadata only; not an observed or required Second runtime dependency')
        r['status']='publisher_metadata_observed'
    except Exception as exc:r.update(status='unavailable',error=dict(type=type(exc).__name__,message=str(exc)))
    return name,r


if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=dict(pool.map(collect,REQUESTS.items()))
    result=dict(schema='submission-publisher-license-metadata-v69',
        captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),items=rows,
        complete_transitive_license_clearance=False,model_or_corpus_content_acquired=False,
        packages_installed=False,project_license_assigned=False,raw_material_redistribution_authorized=False,
        scope='Publisher declarations only; actual package notices and rights review remain separate')
    print(json.dumps(result,sort_keys=True,indent=2))
