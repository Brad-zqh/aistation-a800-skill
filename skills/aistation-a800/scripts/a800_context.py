"""Read configured context and current worker identity without printing secrets."""
import argparse
import json
from pathlib import Path
import os
import shlex
import subprocess
from a800_probe import load_profile,ssh_argv,ProbeError,relative_remote

DEFAULT=Path('E:/CodexData/private/aistation-a800/current.local.json')

def context(cfg):
    p=cfg.get('platform',{});projects=cfg.get('project_runtimes',{})
    return {'status':'configuration_inventory_not_live_platform_submission','platform_URL_configured':bool(p.get('base_url')),'authentication_reference_configured':bool(p.get('authentication_reference')),
      'operations_script_count':len(p.get('known_operations_scripts',[])),
      'operations_scripts_exist':[Path(x).is_file() for x in p.get('known_operations_scripts',[])],
      'project_keys':sorted(projects),'independently_submitted_new_task_not_implied':True,
      'SSH_key_file_exists':Path(cfg['ssh']['identity_file']).is_file(),'known_hosts_exists':Path(cfg['ssh']['known_hosts']).is_file()}

REMOTE=r'''
import json,os,time
from pathlib import Path
root=Path(settings['root']);safe={}
for role in ['worker_state','supervisor_state']:
 p=root/settings[role]
 if p.is_file():safe[role]=json.loads(p.read_text())
sup=safe.get('supervisor_state',{});job=safe.get('worker_state',{})
identity=sup.get('worker_identity') or {'pid':job.get('pid'),'proc_start_ticks':job.get('proc_start_ticks')}
pid=identity.get('pid');proc=Path('/proc/'+str(pid));matches=False;expected=False;state_is_current=False
if pid and (proc/'stat').is_file():
 s=(proc/'stat').read_text().rsplit(')',1)[1].split()
 matches=s[0]!='Z' and int(s[19])==identity.get('proc_start_ticks')
 command=(proc/'cmdline').read_bytes().split(b'\0')
 expected=any(x.decode(errors='replace')==str(root/settings['worker_entry']) for x in command)
 state_is_current=matches and job.get('pid')==pid and job.get('proc_start_ticks')==identity.get('proc_start_ticks')
allowed={'status','stage','updated_utc','started_utc','completed_windows','completed_sources','actual_dense_frames','sources_completed','actual_semantic_frames','current_window','pid','proc_start_ticks'}
print(json.dumps({'status':'current_worker_identity_verified' if matches and expected else 'no_matching_live_project_worker',
 'hostname':os.uname().nodename,'PID1_start_ticks':Path('/proc/1/stat').read_text().rsplit(')',1)[1].split()[19],
 'worker_alive_identity_matches':matches,'expected_script_matches':expected,'recorded_state_belongs_to_current_worker':state_is_current,
 'safe_worker_state':{k:v for k,v in job.items() if k in allowed},'platform_task_ID_verified':bool(settings.get('platform_task_id_verified')),
 'old_status_running_is_not_live_evidence':True,'no_remote_mutations':True}))
'''

def worker(cfg,key):
    settings=cfg.get('project_runtimes',{}).get(key)
    if not settings:raise ProbeError('project_runtime_not_registered')
    for name in ['worker_state','supervisor_state','worker_entry']:relative_remote(settings[name])
    if not settings['root'].startswith('/') or '\n' in settings['root']:raise ProbeError('invalid_project_root')
    payload='settings='+repr(settings)+'\n'+REMOTE
    r=subprocess.run(ssh_argv(cfg)+[shlex.quote(cfg['remote']['python'])+' -B -'],input=payload,capture_output=True,text=True,timeout=60)
    if r.returncode:raise ProbeError('worker_identity_probe_failed')
    return json.loads(r.stdout)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['context','worker']);p.add_argument('--profile',type=Path,default=Path(os.environ.get('AISTATION_A800_PROFILE',str(DEFAULT))));p.add_argument('--project');a=p.parse_args()
    cfg=load_profile(a.profile)
    result=context(cfg) if a.mode=='context' else worker(cfg,a.project)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except ProbeError as error:print(json.dumps({'status':'not_verified','safe_error_code':str(error)}));raise SystemExit(2)
