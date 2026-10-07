"""Acquire pinned public pilot inputs. No remote model code is executed."""
import argparse
import hashlib
import json
from pathlib import Path
import zlib


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=p.parse_args();root=args.root.resolve()
    from huggingface_hub import hf_hub_download
    import httpx
    sources=[('model','distilbert/distilgpt2','2290a62682d06624634c1f46a6ad5be0f47f38aa','tmp/models/distilgpt2',
        ['config.json','model.safetensors','tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','README.md']),
        ('model','openai-community/gpt2','607a30d783dfa663caf39e06633721c8d4cfcd7e','tmp/models/gpt2',['config.json']),
        ('dataset','Salesforce/wikitext','b08601e04326c79dfdd32d625aee71d232d685c3','tmp/data/wikitext2',
        ['README.md','wikitext-2-raw-v1/train-00000-of-00001.parquet','wikitext-2-raw-v1/validation-00000-of-00001.parquet']),
        ('dataset','EleutherAI/lambada_openai','900124bf3b8235c6daf21033af9948b3f07346c4','tmp/data/lambada',
        ['README.md','data/lambada_test_en.jsonl'])]
    rows=[]
    expected=json.loads((root/'pilots/v10/acquired-files.json').read_text()) if (root/'pilots/v10/acquired-files.json').exists() else {}
    for kind,repo,revision,directory,files in sources:
        for filename in files:
            path=Path(hf_hub_download(repo,filename,repo_type=kind,revision=revision,local_dir=root/directory))
            with path.open('rb') as f:hashed=hashlib.file_digest(f,'sha256').hexdigest()
            key=str(path.relative_to(root))
            if key in expected and hashed!=expected[key]['sha256']:
                raise ValueError('download hash differs: '+key)
            rows.append(dict(path=key,repo=repo,revision=revision,sha256=hashed,bytes=path.stat().st_size))
    # A declared bounded byte prefix, not a sample from the complete C4 corpus.
    url='https://huggingface.co/datasets/allenai/c4/resolve/1588ec454efa1a09f29cd18ddd04fe05fc8653a2/en/c4-train.00000-of-01024.json.gz'
    with httpx.Client(timeout=60,follow_redirects=True) as client:
        with client.stream('GET',url,headers={'Range':'bytes=0-2097151'}) as response:
            response.raise_for_status()
            if response.status_code!=206 or response.headers.get('content-range')!='bytes 0-2097151/319308785':
                raise ValueError('C4 source range differs')
            raw=b''
            for block in response.iter_bytes(65536):
                raw+=block
                if len(raw)>2097152:raise ValueError('C4 range exceeded')
    if hashlib.sha256(raw).hexdigest()!='57860fc6417c605d92606dd2ad1490bab9f619cc0f5cbf49117dc520e8f65403':
        raise ValueError('C4 prefix hash differs')
    out=root/'tmp/data/c4';out.mkdir(parents=True,exist_ok=True)
    (out/'prefix.gz.part').write_bytes(raw)
    dec=zlib.decompressobj(16+zlib.MAX_WBITS);body=dec.decompress(raw,32*1024*1024)
    records=[]
    for line in body.splitlines():
        try:records.append(json.loads(line))
        except json.JSONDecodeError:break
    (out/'records.json').write_text(json.dumps(records))
    print(json.dumps({'files':len(rows),'C4_records':len(records),'model_code_executed':False}))


if __name__=='__main__':main()
