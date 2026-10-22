"""Read-only AIStation inspection. Python3.8+; no credential or source logging."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys


class ProbeError(Exception):
    """Only stable symbolic codes may be emitted for local errors."""


def inside(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def relative_remote(value):
    p=PurePosixPath(value)
    if not value or p.is_absolute() or '..' in p.parts or '\\' in value or '\n' in value:
        raise ProbeError('invalid_remote_relative_path')
    return value


def load_profile(path):
    cfg=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if cfg.get('schema_version')!=1:raise ProbeError('unsupported_profile_schema')
    ssh=cfg['ssh'];remote=cfg['remote']
    if set(ssh)-{'executable','host','port','user','identity_file','known_hosts'}:
        raise ProbeError('unexpected_ssh_field_no_inline_credentials')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*',ssh['host']):raise ProbeError('invalid_host')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*',ssh['user']):raise ProbeError('invalid_user')
    if type(ssh['port']) is not int or not 1<=ssh['port']<=65535:raise ProbeError('invalid_port')
    for value in [remote['project_root'],remote['python']]:
        if not PurePosixPath(value).is_absolute() or '\n' in value or '\r' in value:
            raise ProbeError('invalid_remote_absolute_path')
    for value in remote.get('state_files',[]):
        relative_remote(value)
        if not value.startswith('state/') or not value.endswith('.json'):raise ProbeError('state_metadata_only')
    for value in remote.get('model_paths',[]):relative_remote(value)
    scratch=Path(cfg['scratch_root']).resolve()
    if os.name=='nt' and scratch.drive.casefold()!='e:':raise ProbeError('scratch_must_resolve_to_E')
    if not scratch.is_dir():raise ProbeError('scratch_missing')
    for name in ['TEMP','TMP','TMPDIR']:os.environ[name]=str(scratch)
    for name in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='2'
    return cfg


def ssh_argv(cfg):
    s=cfg['ssh'];exe=shutil.which(s.get('executable','ssh'))
    if not exe:raise ProbeError('ssh_executable_missing')
    for key in ['identity_file','known_hosts']:
        if not Path(s[key]).is_file():raise ProbeError(key+'_missing')
    return [exe,'-T','-p',str(s['port']),'-i',s['identity_file'],
            '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
            '-o','UserKnownHostsFile='+s['known_hosts'],'-o','ConnectTimeout=10',
            s['user']+'@'+s['host']]


def local_probe(cfg):
    args=ssh_argv(cfg)
    return {'status':'local_preflight_pass','python':sys.executable,
            'configured_python_exists':Path(cfg['local_python']).is_file(),
            'scratch_root':str(Path(cfg['scratch_root']).resolve()),
            'scratch_free_bytes':shutil.disk_usage(cfg['scratch_root']).free,
            'ssh_executable':args[0],'strict_host_checking':True,'credential_contents_read':False}


def count_checkpoint(path, roots):
    p=Path(path)
    if 'NO_TEXT' not in p.name or p.suffix!='.jsonl':raise ProbeError('no_text_checkpoint_required')
    if not any(inside(p,Path(root)) for root in roots):raise ProbeError('checkpoint_outside_approved_private_roots')
    count=0;valid=0;seen=set();duplicates=0;partial=False
    prohibited={'text','body','quote','raw_reply','review_pros','review_cons','review_advice','tokens'}
    with p.open('rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'):partial=True;break
            if not line.strip():continue
            row=json.loads(line)
            if not isinstance(row,dict) or prohibited.intersection(row):raise ProbeError('unexpected_body_or_raw_payload')
            count+=1;valid+=row.get('valid') is True
            ident=row.get('item',row.get('review_id',row.get('frame_id')))
            if ident is not None:
                duplicate=ident in seen;duplicates+=duplicate;seen.add(ident)
    return {'complete_rows':count,'valid_true_rows':valid,'duplicate_ID_rows':duplicates,
            'trailing_partial_ignored':partial,'checkpoint_modified':False,'individual_records_exported':False}


REMOTE_CODE=r'''
import datetime,hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
try:
 root=Path(cfg['project_root']).resolve();assert root.is_dir()
 safe={'UTC','stage','worker_PID','server_PID','supervisor_PID','generation','completed_HTTP_calls','exit_codes'}
 result={'status':'remote_probe_completed','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'python':sys.executable,'python_version':sys.version.split()[0],'project_exists':True,'states':{},'cgroup':{}}
 for name in cfg.get('state_files',[]):
  path=(root/name).resolve();assert os.path.commonpath([str(root),str(path)])==str(root)
  if not path.is_file():result['states'][name]={'present':False};continue
  value=json.loads(path.read_text());result['states'][name]={'present':True,**{k:v for k,v in value.items() if k in safe}}
 for name in ['memory.max','memory.current','cpu.max']:
  path=Path('/sys/fs/cgroup')/name
  result['cgroup'][name]=path.read_text().strip() if path.is_file() else None
 gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.free,memory.used,utilization.gpu','--format=csv,noheader,nounits'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
 result['GPU_query_returncode']=gpu.returncode
 result['GPU']=gpu.stdout.decode('utf-8',errors='replace').strip() if gpu.returncode==0 else None
 if hash_models:
  result['model_SHA256']={}
  for name in cfg.get('model_paths',[]):
   path=(root/name).resolve();assert os.path.commonpath([str(root),str(path)])==str(root)
   h=hashlib.sha256()
   with path.open('rb') as f:
    for b in iter(lambda:f.read(2**20),b''):h.update(b)
   result['model_SHA256'][name]=h.hexdigest()
 print(json.dumps(result))
except Exception as exc:
 print(json.dumps({'probe_error_type':type(exc).__name__,'locations':[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(exc.__traceback__)]}))
 sys.exit(1)
'''


def remote_probe(cfg, hash_models=False):
    prefix='cfg=json.loads('+repr(json.dumps(cfg['remote']))+')\nhash_models='+repr(hash_models)+'\n'
    program='import json\n'+prefix+REMOTE_CODE
    command=ssh_argv(cfg)+[shlex.quote(cfg['remote']['python'])+' -B -']
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    result=subprocess.run(command,input=program.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          timeout=180 if hash_models else 45,**options)
    try:value=json.loads(result.stdout)
    except (ValueError,UnicodeDecodeError):raise ProbeError('ssh_or_remote_probe_failed_code_'+str(result.returncode))
    if result.returncode:raise ProbeError('remote_probe_failed_code_'+str(result.returncode))
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['local','remote','count'])
    parser.add_argument('--profile',default=os.environ.get('AISTATION_A800_PROFILE','E:/CodexData/private/aistation-a800/current.local.json'))
    parser.add_argument('--path');parser.add_argument('--hash-models',action='store_true')
    args=parser.parse_args();cfg=load_profile(args.profile)
    if args.mode=='local':result=local_probe(cfg)
    elif args.mode=='remote':result=remote_probe(cfg,args.hash_models)
    else:
        if not args.path:raise ProbeError('checkpoint_path_required')
        result=count_checkpoint(args.path,cfg.get('private_checkpoint_roots',[]))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        value={'error_type':type(exc).__name__}
        if isinstance(exc,ProbeError):value['code']=str(exc)
        print(json.dumps(value));raise SystemExit(1)
