"""One-use held/release and prior-operation guards for complete matched workers."""
from research_v80.io import require,json_read
from research_v111.config import RUN,OPERATIONS,name,cpu

def allocation(operation,expected,job,*,require_release=False):
    key=name(operation);require(type(job) is str and job.isdigit(),'Actual Slurm job required')
    row=json_read(RUN/(key+'-submission.json'))
    require(row['name']==key and row['operation']==operation and row['arguments']==[]
        and row['program_sha256']==expected and row['job_id']==job,'Literal matched allocation differs')
    mode='checks' if operation=='checks' else 'chain';held=json_read(RUN/(mode+'-held-chain.json'))
    require(held['program_sha256']==expected and sum(r==row for r in held['jobs'])==1,'Actual validated held chain required')
    if require_release:
        require(json_read(RUN/(key+'-release.json'))==dict(program_sha256=expected,job_id=job,released=True),
            'Actual one-use release required')

def earlier(operation,expected):
    for op in OPERATIONS[:OPERATIONS.index(operation)]:
        key=name(op);e=json_read(RUN/(key+'-entry.json'));h=json_read(RUN/(key+'-host.json'))
        require(e['status']==h['status']=='complete' and e['error'] is h['error'] is None
            and e['program_sha256']==h['program_sha256']==expected and e['job_id']==h['job_id']
            and e['operation']==h['operation']==op and e['arguments']==h['arguments']==[], 'Earlier operation not complete')
        allocation(op,expected,e['job_id'],require_release=True)
        require(e['container_storage_mapping']['status']=='matched_host_devices_and_new_file_groups'
            and h['accounting']['nonnumerical_cpu_ns']<=cpu(op)[2]*10**9,'Earlier complete controller/mapping failed')
        if op=='checks':
            from research_v111.software import validate
            validate(e['result'])
