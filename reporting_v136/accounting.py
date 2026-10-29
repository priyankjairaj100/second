from pathlib import Path
import subprocess,json,datetime,decimal,sys
r=Path('/Users/priyankjairaj/Downloads/ACL/Second')
families={'V124':[16677,16678,16679],'V125':list(range(16681,16689)),'V126':[16689],'V127':[16690],'V128':[16693],'V129':[16694,16696,16697,16698,16699],'V130':[16695,16700,16701,16702,16703],'V131':[16704,16705,16706,16707],'V132':[16708,16711,16712,16713,16714],'V133':[16717,16718,16719,16720]}
f=r/'pilots/control-quality-v134-20261029/initial-submission.json'
if f.exists():families['V134']=list(json.loads(json.loads(f.read_text())['stdout'])['jobs'].values())
f=r/'pilots/control-quality-v136-20261029/initial-submission.json'
if f.exists():families['V136']=list(json.loads(json.loads(f.read_text())['stdout'])['jobs'].values())
ids=[j for v in families.values() for j in v];assert len(set(ids))==len(ids)
z=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','csis','sacct -j '+','.join(map(str,ids))+' -P --format=JobIDRaw,JobName,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS'],capture_output=True,text=True,check=True)
lines=z.stdout.splitlines();headers=lines[0].split('|');rows={v.split('|')[0]:dict(zip(headers,v.split('|'))) for v in lines[1:]}
def seconds(s):
 days=0
 if '-' in s:day,s=s.split('-',1);days=int(day)
 parts=list(map(decimal.Decimal,s.split(':')));result=decimal.Decimal(86400*days)
 for i,x in enumerate(reversed(parts)):result+=x*60**i
 return result
out={}
for n,js in families.items():
 rs=[rows[str(j)] for j in js];terminal=all(x['State'] in ['COMPLETED','FAILED','TIMEOUT','CANCELLED'] for x in rs)
 if terminal:assert all(x['AllocCPUS']=='1' for x in rs)
 out[n]=dict(jobs=rs,terminal=terminal,total_cpu_seconds=str(sum((seconds(x['TotalCPU']) for x in rs),decimal.Decimal(0))))
report=dict(schema='revision-quality-actual-accounting-v134',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),families=out,total_cpu_seconds=str(sum((decimal.Decimal(x['total_cpu_seconds']) for x in out.values()),decimal.Decimal(0))),all_terminal=all(x['terminal'] for x in out.values()),scope='Slurm TotalCPU of distinct top-level allocations; batch/extern rows not double-counted; launcher/controller CPU not measured here')
outfile=r/'pilots/control-quality-v136-20261029'/sys.argv[1]
with outfile.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({n:{k:x[k] for k in ['terminal','total_cpu_seconds']} for n,x in out.items()},indent=2));print('TOTAL',report['total_cpu_seconds'])
