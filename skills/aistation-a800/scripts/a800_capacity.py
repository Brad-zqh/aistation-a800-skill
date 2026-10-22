"""Read-only multi-sample GPU capacity, ownership and cgroup inspection (Python3.8+)."""
import argparse
import csv
import datetime
import json
import os
from pathlib import Path
import shlex
import statistics
import subprocess
from a800_probe import ProbeError,load_profile,ssh_argv


def summarize(samples):
    """Keep unavailable metrics unavailable; never substitute zero or mix GPUs."""
    devices={}
    for sample in samples:
        for row in sample:
            device=devices.setdefault(row['uuid'],{'name':row['name'],'samples':[]})
            device['samples'].append(row)
    output=[]
    for uuid,device in sorted(devices.items()):
        result={'uuid':uuid,'name':device['name'],'samples':len(device['samples'])}
        for metric in ('GPU_util_percent','memory_util_percent','used_MiB','free_MiB','total_MiB','power_W'):
            values=[row[metric] for row in device['samples'] if row.get(metric) is not None]
            result[metric]={'observed':len(values),'min':min(values),'mean':statistics.mean(values),'max':max(values)} if values else None
        output.append(result)
    return output


REMOTE=r'''
import csv,datetime,json,os,subprocess,time,traceback
from pathlib import Path
try:
 def number(s):
  try:return float(s.strip())
  except ValueError:return None
 def query(args):
  r=subprocess.run(['nvidia-smi']+args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,universal_newlines=True)
  if r.returncode:raise RuntimeError('GPU_query_failed')
  return list(csv.reader(r.stdout.splitlines(),skipinitialspace=True))
 samples=[]
 for i in range(settings['samples']):
  current=[]
  for row in query(['--query-gpu=uuid,name,utilization.gpu,utilization.memory,memory.used,memory.free,memory.total,power.draw','--format=csv,noheader,nounits']):
   if len(row)!=8:raise ValueError('unexpected_GPU_columns')
   z={'uuid':row[0].strip(),'name':row[1].strip()}
   z.update(dict(zip(['GPU_util_percent','memory_util_percent','used_MiB','free_MiB','total_MiB','power_W'],map(number,row[2:]))));current.append(z)
  samples.append(current)
  if i+1<settings['samples']:time.sleep(settings['interval'])
 processes=[]
 for row in query(['--query-compute-apps=pid,gpu_uuid,process_name,used_memory','--format=csv,noheader,nounits']):
  if len(row)!=4:continue
  pid=int(row[0]);p=Path('/proc')/str(pid);projects=[];ticks=None
  try:
   command=[v.decode(errors='replace') for v in (p/'cmdline').read_bytes().split(b'\0') if v]
   ticks=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])
   for key,root in settings['project_roots'].items():
    if any(token==root or token.startswith(root.rstrip('/')+'/') for token in command):projects.append(key)
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
  processes.append({'PID':pid,'start_ticks':ticks,'GPU_uuid':row[1].strip(),'executable_basename':Path(row[2].strip()).name,'used_MiB':number(row[3]),'registered_project_matches':sorted(projects),'owner_verified':len(projects)==1})
 cgroup={}
 for key in ['memory.max','memory.current','cpu.max']:
  p=Path('/sys/fs/cgroup')/key;cgroup[key]=p.read_text().strip() if p.is_file() else None
 print(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'samples':samples,'CUDA_processes':processes,'cgroup':cgroup,'whole_device_shared_utilization':True,'worker_or_checkpoint_completion_not_implied':True,'remote_mutations':False}))
except Exception as e:
 print(json.dumps({'error_type':type(e).__name__,'locations':[{'file':Path(x.filename).name,'line':x.lineno} for x in traceback.extract_tb(e.__traceback__)]}));raise SystemExit(1)
'''


def inspect(cfg,samples=12,interval=1):
    if type(samples) is not int or not 1<=samples<=60 or not 0<=interval<=10 or (samples-1)*interval>50:
        raise ProbeError('sampling_window_must_be_at_most_50_seconds')
    roots={key:value['root'] for key,value in cfg.get('project_runtimes',{}).items() if value.get('root')}
    settings={'samples':samples,'interval':interval,'project_roots':roots}
    code='settings='+repr(settings)+'\n'+REMOTE
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    r=subprocess.run(ssh_argv(cfg)+[shlex.quote(cfg['remote']['python'])+' -B -'],input=code.encode('utf8'),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=60,**options)
    if r.returncode:raise ProbeError('remote_capacity_probe_failed')
    value=json.loads(r.stdout);value['GPU_summary']=summarize(value.pop('samples'));return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',default=os.environ.get('AISTATION_A800_PROFILE','E:/CodexData/private/aistation-a800/current.local.json'));p.add_argument('--samples',type=int,default=12);p.add_argument('--interval',type=float,default=1);a=p.parse_args()
    print(json.dumps(inspect(load_profile(a.profile),a.samples,a.interval),ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except Exception as e:
        out={'error_type':type(e).__name__}
        if isinstance(e,ProbeError):out['safe_code']=str(e)
        print(json.dumps(out));raise SystemExit(1)
