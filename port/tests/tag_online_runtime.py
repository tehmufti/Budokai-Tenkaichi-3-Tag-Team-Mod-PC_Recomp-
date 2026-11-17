"""Native rooms using actual player and spectator processes; no external server."""
import os, pathlib, subprocess, time, argparse, re, signal, sys
p=argparse.ArgumentParser()
p.add_argument('--bt4', action='store_true')
p.add_argument('--exe',type=pathlib.Path,help='Native executable to exercise')
p.add_argument('--data',type=pathlib.Path,help='Imported disc folder (including regional profiles)')
p.add_argument('--party', action='store_true', help='Persistent practice lobby transport')
p.add_argument('--late-join', action='store_true', help='Wait for the first practice frame 1200 before the third connection')
p.add_argument('--rejoin', action='store_true', help='Replace the first guest after their practice fighter change')
p.add_argument('--join-in-match', action='store_true', help='Connect the third member during a match, then check the practice return')
p.add_argument('--party-mode',type=int,default=1,choices=range(5))
p.add_argument('--spectators', type=int, default=0)
p.add_argument('--players', type=int, default=2, choices=range(1,11))
p.add_argument('--host-spectator', action='store_true')
p.add_argument('--swap-roles', action='store_true', help='Host and first spectator exchange seats, then swap back after a round')
p.add_argument('--high-fusion', action='store_true', help='Give the fusion pair to Players 9 and 10')
p.add_argument('--frames', type=int, default=600)
p.add_argument('--timeout', type=int, default=90)
p.add_argument('--startup-timeout',type=int,default=600,help='Allow a first-run BT4 content fingerprint to finish')
p.add_argument('--audit', action='store_true')
p.add_argument('--input', action='store_true')
p.add_argument('--host-speed',type=int,default=100)
p.add_argument('--guest-speed',type=int,default=100)
p.add_argument('--lag', action='store_true')
p.add_argument('--size', help='Team sizes; cinematic fixtures default to their authored 2v2 setup, other cases to 5v5')
p.add_argument('--case', type=int, default=0)
p.add_argument('--label', default='latest')
p.add_argument('--rounds', type=int, default=0)
p.add_argument('--watch-camera', action='store_true')
p.add_argument('--gpu', action='store_true')
p.add_argument('--gpu-client', help='Render only this client (for example player9); other clients run headless')
p.add_argument('--capture-ms', type=int, default=0, help='Save each GPU window at this time after startup')
p.add_argument('--sound', action='store_true', help='Exercise the real audio backend')
p.add_argument('--disconnect', choices=['host','guest','watch0'])
p.add_argument('--kick', action='store_true', help='Host removes the first practice guest; other members continue')
p.add_argument('--port', type=int, default=17001)
p.add_argument('--load-delay', type=int, default=0, help='Delay only the guest loading check by this many milliseconds')
p.add_argument('--load-delay-round', type=int, default=0, help='Delay only this room round (2 is the first lobby match); 0 delays every load')
p.add_argument('--freeze', help='Suspend this client, sockets left open, once every client has logged --freeze-at in a match')
p.add_argument('--freeze-at', type=int, default=600, help='Match blank (a multiple of 600) every client logs before the freeze')
p.add_argument('--freeze-seconds', type=float, default=0, help='Resume the frozen client after this long; 0 keeps it frozen')
p.add_argument('--no-fighter', help='This lobby member never claims a fighter and watches the match')
p.add_argument('--join-in-setup', action='store_true', help='Connect the third member while the host shows the team setup page')
p.add_argument('--paced', action='store_true', help='Every client runs at display speed')
p.add_argument('--then-return', action='store_true', help='After a freeze or a late join the others must also finish the match and be back in practice')
p.add_argument('--hold-start', help='This client holds Start whenever it waits for the others')
p.add_argument('--language', action='append', default=[], metavar='[CLIENT:]CODE', help='Menu language of every client or of one, for example es or host:es')
p.add_argument('--capture', action='append', default=[], metavar='CLIENT:MS', help='Render this client and save its window this long after its start')
p.add_argument('--draft', help='Host test switch: tournament team of each of the ten setup slots, for example 0,0,1,1,2,2,3,3,0,1')
p.add_argument('--expect', action='append', default=[], metavar='CLIENT:TEXT', help='This text must appear in that client log')
p.add_argument('--reject', action='append', default=[], metavar='CLIENT:TEXT', help='This text must not appear in that client log')
p.add_argument('--input-spread', action='store_true', help='With --input: every player changes its input on its own blanks')
p.add_argument('--slow', action='append', default=[], metavar='CLIENT:MS', help='Every blank of this client takes this long more')
p.add_argument('--hitch', action='append', default=[], metavar='CLIENT:BLANK:MS', help='This client stands still once, at this match blank, for this long')
p.add_argument('--net-balance', choices=['0','1'], help='Clock balance off or on, on every client')
p.add_argument('--net-input-delay', help='Input delay in blanks chosen by the host (2 to 5); auto leaves the choice to the measured pings')
p.add_argument('--net-window', type=int, help='Prediction window in blanks, on every client')
p.add_argument('--proxy', type=pathlib.Path, help='Delay proxy script; every guest and spectator then joins through it')
p.add_argument('--proxy-delay', type=float, default=0, help='Milliseconds each way')
p.add_argument('--proxy-stall', metavar='MS:SECONDS', help='A stall of MS on every proxied connection every SECONDS')
p.add_argument('--differ', metavar='CLIENT:BLANK[:FIGHTER]', help='This client alone changes one fighter at this match blank; both sides must write a mismatch report')
p.add_argument('--stats-from', type=int, default=600, help='The summary counts the periodic lines after this match blank')
p.add_argument('--until-decided', action='store_true', help='With --freeze: the other clients must also play the match to its result')
p.add_argument('--teams', type=int, choices=range(2,6), help='Host test switch: the lobby plays Team Battle with this many teams (with --party --rounds --party-mode 0)')
p.add_argument('--team', action='append', default=[], metavar='CLIENT:TEAM', help='This member takes a free fighter of that team (1..5) before it readies')
p.add_argument('--move', action='append', default=[], metavar='CLIENT:TEAM', help='This member moves its own fighter to that team before it readies, with the edit L1 / R1 send')
p.add_argument('--match-time', type=int, choices=range(6), help='Host test switch: the time rule of the Team Battle (0 none, 1 60 s, 2 90 s, 3 180 s, 4 240 s, 5 45 s)')
p.add_argument('--bad-teams', action='store_true', help='The host sends its guests a room whose last team is empty; every guest must refuse it')
p.add_argument('--team-differ', metavar='CLIENT:SLOT', help='This client alone puts the fighter of that setup slot on another team; the match must stop with a mismatch report naming the team')
p.add_argument('--host-pad', help='Scripted pad of a rendered host (frame:button,...); the host then chooses the mode in its menu itself and never readies')
p.add_argument('--shots', action='append', default=[], metavar='CLIENT:FRAME,FRAME,...', help='Render this client and save its window at these frames; the run ends when the last one exists')
p.add_argument('--env', action='append', default=[], metavar='NAME=VALUE', help='One more environment variable for every client (diagnostic switches)')
a=p.parse_args()
differ=a.differ or a.team_differ
assert not a.teams or (a.party and a.rounds and a.party_mode==0) or a.host_pad
if a.size is None:a.size='2,2' if a.case in (6,7) else '5,5'
# The host waits on the setup page only while the first guest has not claimed a fighter.
assert not a.join_in_setup or (a.party and a.rounds and a.no_fighter=='guest' and a.players==3)
root=pathlib.Path(__file__).resolve().parents[2]
exe=(a.exe or root/'port/build/bt3.exe').resolve()
out=root/'port/build/tag-online'/a.label
out.mkdir(parents=True,exist_ok=True)
env={k:v for k,v in os.environ.items() if not k.startswith('BT3_')}
env.update(BT3_TAG_TEAM='1', BT3_TAG_ONLINE='1', BT3_TAG_AUTO_READY='1',
           BT3_TAG_TEST_PLAYERS=str(a.players),
           BT3_DATA=str((a.data or root/('gamedata-bt4' if a.bt4 else 'gamedata')).resolve()),
           BT3_NOSOUND='1', BT3_GS='none', BT3_UPDATE_CHECK='0', BT3_TEST_FRAMES='0')
if a.disconnect or a.kick:env['BT3_TAG_SAVE_CHECK']='1'
if a.kick:
    assert a.party and a.players>=3
    env['BT3_TAG_TEST_KICK']='1'
if a.audit:env['BT3_TAG_NET_AUDIT']='1'
if a.party:env['BT3_TAG_PARTY']='1'
if a.late_join or a.join_in_match or a.join_in_setup:env['BT3_TAG_TEST_PLAYERS']='2'
if a.party and a.rounds:env['BT3_TAG_PARTY_FLOW']=str(a.party_mode)
if a.party and a.rounds:env['BT3_TAG_TEST_ROUNDS']=str(a.rounds)
if a.teams:env['BT3_TAG_TEST_TEAMS']=str(a.teams)
for item in a.env:env[item.split('=',1)[0]]=item.split('=',1)[1]
if a.match_time is not None:env['BT3_TAG_TEST_TIME']=str(a.match_time)
if a.bad_teams:env['BT3_TAG_TEST_BAD_TEAMS']='1'
if a.input:env['BT3_TAG_TEST_INPUT']='2' if a.input_spread else '1'
if a.net_balance:env['BT3_TAG_NET_BALANCE']=a.net_balance
if a.net_input_delay and a.net_input_delay!='auto':env['BT3_TAG_NET_DELAY']=a.net_input_delay
if a.net_window:env['BT3_TAG_NET_WINDOW']=str(a.net_window)
if a.lag:env['BT3_TAG_TEST_LAG']='1'
if a.swap_roles:env['BT3_TAG_TEST_ROLE_SWAP']='1'
if a.high_fusion:env['BT3_TAG_TEST_HIGH_FUSION']='1'
if a.watch_camera:env['BT3_TAG_NET_WATCH_TEST']='1'
if a.gpu:env['BT3_GS']='gpu'
if a.gpu or a.gpu_client:env['BT3_TAG_CAMERA_TRACE']='1'
if a.sound:
    env.pop('BT3_NOSOUND',None)
    env['BT3_SOUND']='1'  # Headless clients must also open their audio backend.
env['BT3_TAG_TEST_SIZE']=a.size
if a.case:env['BT3_TAG_NET_CASE']=str(a.case)
if a.case==3:env['BT3_TAG_TEST_BEAM_ASSIST']='1'
if a.case==4:env['BT3_TAG_TEST_MULTI_BEAMS']='1'
if a.case in (6,7):env['BT3_TAG_TEST_CINEMA']=str(a.case-5)
jobs=[];completed=False;disconnected=False;disconnect_at=None;rejoined=False
# Members that are expected to drop out while the others keep playing.
victims={a.freeze,a.hold_start,'guest' if a.party and a.load_delay else None}-{None}
watched=bool(a.freeze or a.join_in_setup or (a.party and a.load_delay))
STOPPED=('match has stopped','Match stopped','The room is closed','before the result was confirmed','did not return from the match','could not finish loading practice')
GONE=('A guest left the practice map.','Lost the connection to Player 2.','Player 2 left.')
began=time.time();timeline=[];seen={};frozen_at=None;resumed_at=None;reached=None;base={};final={}
proxy=None;join_port=a.port+1 if a.proxy else a.port;started={};used={}
STATS=re.compile(r'frame (\d+), confirmed \d+, players \d+, rewinds \d+, speed \d+%, in (\d+) ms: rollbacks (\d+), depth ([\d.]+) max (\d+), resim ([\d.]+) ms max ([\d.]+) ms, '
                 r'waits (\d+), waited (\d+) ms, ahead (-?[\d.]+), slowed (\d+) ms, delay (\d+), window (\d+)')

def settings_file(name):
    # A mismatch report is written beside the settings file: then every client needs a folder of its own.
    if not differ and not a.teams:return out/(name+'.settings')
    (out/('home-'+name)).mkdir(exist_ok=True)
    return out/('home-'+name)/'settings.txt'

def cpu_seconds(proc):
    # Processor time a client has used so far (Windows only): how much of a core a copy needs.
    if sys.platform!='win32' or proc.poll() is not None:return None
    import ctypes
    t=[ctypes.c_ulonglong() for _ in range(4)]
    if not ctypes.windll.kernel32.GetProcessTimes(ctypes.c_void_p(int(proc._handle)),*[ctypes.byref(v) for v in t]):return None
    return (t[2].value+t[3].value)/1e7

def summary(name,content):
    # One line per client from the periodic lines of the match after --stats-from, up to --frames (the same
    # stretch on every client, whichever of them was the last to confirm it).
    rows=[m.groups() for m in STATS.finditer(match_part(name,content)) if a.stats_from<int(m.group(1))<=max(a.frames,a.stats_from+600)]
    if not rows:return None
    rolls=sum(int(r[2]) for r in rows);ms=sum(int(r[1]) for r in rows);blanks=600*len(rows)
    return ('STATS %-8s blanks %d in %d ms (%.1f per second), rollbacks %d, depth %.2f max %d, resim %.2f ms max %.2f ms, waits %d, waited %d ms, ahead %.2f, slowed %d ms, delay %s, window %s'%(
        name,blanks,ms,blanks*1000/max(ms,1),rolls,sum(float(r[3])*int(r[2]) for r in rows)/max(rolls,1),max(int(r[4]) for r in rows),
        sum(float(r[5])*int(r[2]) for r in rows)/max(rolls,1),max(float(r[6]) for r in rows),sum(int(r[7]) for r in rows),sum(int(r[8]) for r in rows),
        sum(float(r[9]) for r in rows)/len(rows),sum(int(r[10]) for r in rows),rows[-1][11],rows[-1][12]))

def match_part(name,content):
    # A lobby loads its practice map first. A member that arrived on the setup page never saw that load.
    parts=content.split('Loading the match...')
    index=2 if a.party and a.rounds and not(a.join_in_setup and name=='player2') else 1
    return parts[index] if len(parts)>index else ''

def confirmed_blank(name,content):
    rows=re.findall(r'frame (\d+), confirmed (\d+),',match_part(name,content))
    return int(rows[-1][1]) if rows else -1

def decided(content):
    # The result of a match of three to five teams, as every copy says it.
    return re.findall(r'tagnet: (Team \d won\.|The match ended in a draw\.)',content)

def suspend(proc,on):
    if sys.platform=='win32':
        import ctypes
        call=ctypes.windll.ntdll.NtSuspendProcess if on else ctypes.windll.ntdll.NtResumeProcess
        assert call(ctypes.c_void_p(int(proc._handle)))==0
    else:os.kill(proc.pid,signal.SIGSTOP if on else signal.SIGCONT)

def back_in_practice(name,content):
    loads=a.rounds*2+(0 if a.join_in_setup and name=='player2' else 1)
    return content.count('Loading the match...')>=loads and 'frame 600,' in content.rsplit('Loading the match...',1)[-1]

def note():
    # What every client said, and when: the evidence for a stalled or dropped member.
    for name,_,_,log in jobs:
        lines=log.read_text(errors='replace').splitlines()
        for line in lines[seen.get(name,0):]:
            if line.startswith('tagnet') and not re.search(r'frame \d+, confirmed \d+,',line):timeline.append((time.time(),name,line))
        seen[name]=len(lines)
expected={1:['PASS 105'],2:['PASS 206'],3:['PASS check=99'],4:['PASS check=99'],6:['PASS check=99'],7:['PASS check=99'],8:['PASS 801','PASS 802','PASS 803'],10:['PASS 2510'],12:['PASS 2512']}
if a.party and a.rounds:expected[9]=['PASS 2500','PASS 2501']

def spawn(name):
    e=env.copy();e['BT3_SAVES']=str(out/('saves-'+name));e['BT3_SETTINGS']=str(settings_file(name))
    for item in a.slow:
        if item.split(':')[0]==name:e['BT3_TAG_TEST_SLOW_MS']=item.split(':')[1]
    for item in a.hitch:
        if item.split(':')[0]==name:e['BT3_TAG_TEST_HITCH']=item.split(':',1)[1]
    if a.differ and a.differ.split(':')[0]==name:e['BT3_TAG_TEST_DIFFER']=a.differ.split(':',1)[1]
    if a.team_differ and a.team_differ.split(':')[0]==name:e['BT3_TAG_TEST_TEAM_DIFFER']=a.team_differ.split(':',1)[1]
    for item in a.team:
        if item.split(':')[0]==name:e['BT3_TAG_TEST_TEAM']=item.split(':')[1]
    for item in a.move:
        if item.split(':')[0]==name:e['BT3_TAG_TEST_TEAM']=item.split(':')[1]+'m'
    if name=='host' and a.host_pad:
        e.update(BT3_GS='gpu',BT3_PAD=a.host_pad)
        for key in ('BT3_TAG_PARTY_FLOW','BT3_TAG_AUTO_READY','BT3_TAG_TEST_ROUNDS'):e.pop(key,None)
    for item in a.shots:
        if item.split(':')[0]==name:
            (out/('shots-'+name)).mkdir(exist_ok=True)
            for old in (out/('shots-'+name)).glob('*.ppm'):old.unlink()
            e.update(BT3_GS='gpu',BT3_UI_SHOTS=item.split(':')[1]+':'+str(out/('shots-'+name))+os.sep)
    pathlib.Path(e['BT3_SETTINGS']).write_text('game_speed='+str(a.host_speed if name=='host' else a.guest_speed)+'\n')
    # Real hosts run at display speed. An uncapped headless host otherwise
    # creates replay history as quickly as a replacement can consume it.
    if name=='host' and (a.rejoin or a.late_join):e['BT3_PACED']='1'
    if a.gpu_client==name:e['BT3_GS']='gpu'
    if a.capture_ms and (not a.gpu_client or a.gpu_client==name):e['BT3_UI_SHOT_MS']=str(a.capture_ms)+':'+(out/(name+'.ppm')).relative_to(root).as_posix()
    pathlib.Path(e['BT3_SAVES']).mkdir(exist_ok=True)
    if name=='guest' and a.load_delay:e['BT3_TAG_TEST_LOAD_DELAY_MS']=str(a.load_delay)
    if name=='guest' and a.load_delay and a.load_delay_round:e['BT3_TAG_TEST_LOAD_DELAY_ROUND']=str(a.load_delay_round)
    if name==a.no_fighter:e.pop('BT3_TAG_PARTY_FLOW',None)
    if name==a.hold_start:e['BT3_TAG_TEST_HOLD_START']='1'
    if name=='host' and a.draft:e['BT3_TAG_TEST_DRAFT']=a.draft
    if a.paced:e['BT3_PACED']='1'
    for language in a.language:
        if ':' not in language or language.split(':')[0]==name:e['BT3_MENU_LANG']=language.split(':')[-1]
    for shot in a.capture:
        if shot.split(':')[0]==name:e.update(BT3_GS='gpu',BT3_UI_SHOT_MS=shot.split(':')[1]+':'+(out/(name+'.ppm')).relative_to(root).as_posix())
    if name=='host' and a.host_spectator:e['BT3_TAG_TEST_HOST_SPECTATOR']='1'
    e['BT3_TAG_HOST' if name=='host' else 'BT3_TAG_WATCH' if name.startswith('watch') else 'BT3_TAG_JOIN']=str(a.port) if name=='host' else '127.0.0.1:'+str(join_port)
    log=out/(('bt4-' if a.bt4 else 'bt3-')+name+'.log')
    f=log.open('w');proc=subprocess.Popen([str(exe)],cwd=root,env=e,stdout=f,stderr=f)
    jobs.append((name,proc,f,log));started[name]=time.time()
    return proc,log

def return_complete(content):
    if not a.party:return content.count('Back in the room.')>=a.rounds
    # Wait for a functioning practice map after the final transition, not
    # merely the message printed before loading starts.
    return (content.count('Loading the match...')>=a.rounds*2+1 and
            'frame 600,' in content.rsplit('Loading the match...',1)[-1])

try:
    roles=['host']+['watch'+str(i) for i in range(a.spectators)]+(['guest'] if a.players>1 or a.host_spectator else [])
    roles+=['player'+str(i) for i in range(2,a.players+int(a.host_spectator))]
    for name in roles:
        if a.join_in_setup and name=='player2':
            until=time.time()+90
            while time.time()<until and 'Choose teams.' not in jobs[0][3].read_text(errors='replace'):time.sleep(.1)
            assert 'Choose teams.' in jobs[0][3].read_text(errors='replace'), 'The host did not reach the team setup page'
            time.sleep(1)
        if (a.late_join or a.join_in_match) and name=='player2':
            until=time.time()+90
            def join_point(log):
                content=log.read_text(errors='replace')
                return ('frame 600,' in content.rsplit('Loading the match...',1)[-1] and content.count('Loading the match...')==2) if a.join_in_match else 'frame 1200,' in content
            while time.time()<until and not all(join_point(log) for _,_,_,log in jobs):time.sleep(.1)
            assert all(join_point(log) for _,_,_,log in jobs), 'Initial clients did not reach the join point'
        proc,log=spawn(name);time.sleep(0.6)
        if name=='host':
            wait=time.time()+a.startup_timeout
            while proc.poll() is None and time.time()<wait and 'Room open.' not in log.read_text(errors='replace'):time.sleep(.2)
            if proc.poll() is not None or 'Room open.' not in log.read_text(errors='replace'):raise RuntimeError('Host did not open room')
            if a.proxy:
                # The stand-in for a line with delay: loopback only, between every guest and the host.
                command=[sys.executable,'-I',str(a.proxy.resolve()),'--listen',str(join_port),'--to',str(a.port),'--delay',str(a.proxy_delay)]
                if a.proxy_stall:command+=['--stall-ms',a.proxy_stall.split(':')[0],'--stall-every',a.proxy_stall.split(':')[1]]
                proxy_log=(out/'proxy.log').open('w')
                proxy=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=proxy_log,stderr=subprocess.STDOUT)
                wait=time.time()+10
                while time.time()<wait and 'listening' not in (out/'proxy.log').read_text(errors='replace'):time.sleep(.05)
                assert proxy.poll() is None and 'listening' in (out/'proxy.log').read_text(errors='replace'),'The delay proxy did not start'
    end=time.time()+a.timeout
    while any(proc.poll() is None for _,proc,_,_ in jobs) and time.time()<end:
        if watched:
            note()
            contents={name:log.read_text(errors='replace') for name,_,_,log in jobs}
            # Nobody outlives a frozen host: that run only records what the guests say, and when.
            others=[(name,proc) for name,proc,_,_ in jobs if name not in victims and a.freeze!='host']
            if a.freeze and frozen_at is None and all(('frame %d,'%a.freeze_at) in match_part(name,contents[name]) for name in contents) and all(proc.poll() is None for _,proc,_,_ in jobs):
                base={name:confirmed_blank(name,contents[name]) for name in contents}
                suspend(next(proc for name,proc,_,_ in jobs if name==a.freeze),True);frozen_at=time.time()
                timeline.append((frozen_at,a.freeze,'FROZEN by the harness; confirmed blanks then: '+', '.join('%s %d'%(n,b) for n,b in base.items())))
            if frozen_at and a.freeze_seconds and resumed_at is None and time.time()-frozen_at>=a.freeze_seconds:
                suspend(next(proc for name,proc,_,_ in jobs if name==a.freeze),False);resumed_at=time.time()
                timeline.append((resumed_at,a.freeze,'RESUMED by the harness'))
            if (not a.freeze or frozen_at) and all(confirmed_blank(name,contents[name])>=base.get(name,0)+a.frames and (not a.then_return or back_in_practice(name,contents[name])) and (not a.until_decided or len(decided(contents[name]))>=a.rounds) for name,_ in others):
                if reached is None:
                    reached=time.time();timeline.append((reached,'harness','every other client has confirmed %d more blanks%s'%(a.frames,' and is back in practice' if a.then_return else '')))
                if not(a.freeze and a.freeze_seconds) or (resumed_at and (time.time()-resumed_at>6 or next(proc for name,proc,_,_ in jobs if name==a.freeze).poll() is not None)):
                    note();completed=True;final={name:log.read_text(errors='replace') for name,_,_,log in jobs};break
            if others and all(proc.poll() is not None for _,proc in others):note();break
            time.sleep(.1);continue
        if a.rejoin and not rejoined and all((name=='host' or 'PASS 2510' in log.read_text(errors='replace')) and 'frame 2400,' in log.read_text(errors='replace') for name,_,_,log in jobs):
            next(proc for name,proc,_,_ in jobs if name=='guest').terminate()
            until=time.time()+10
            while time.time()<until and not any(s in jobs[0][3].read_text(errors='replace') for s in GONE):time.sleep(.1)
            assert any(s in jobs[0][3].read_text(errors='replace') for s in GONE)
            spawn('replacement');rejoined=True
        if a.bad_teams:
            # Every guest refuses the room and leaves; the host stays alone on its setup page.
            if all('unsupported fighters' in log.read_text(errors='replace') for name,_,_,log in jobs if name!='host') and len(jobs)==len(roles):
                time.sleep(1);completed=True;break
            time.sleep(.2);continue
        if a.shots:
            if all(any((out/('shots-'+item.split(':')[0])).glob('*'+item.split(',')[-1]+'.ppm')) for item in a.shots):
                time.sleep(.5);completed=True;break
            time.sleep(.2);continue
        if differ:
            # The room must stop by itself, every copy saying why.
            if all('went out of sync' in log.read_text(errors='replace') for _,_,_,log in jobs):
                time.sleep(1);completed=True;break
            time.sleep(.2);continue
        party_done=a.party and not a.rounds and not a.disconnect and all('frame 1200,' in log.read_text(errors='replace') for _,_,_,log in jobs)
        # Online battles enter through the room, not the attract demo. Its
        # BT3_TEST_FRAMES counter measures battle-clock changes, accumulates
        # across rounds, and can exit before a room return completes. The
        # harness owns this deadline and waits for every client's actual
        # confirmed frames and the requested gameplay checks instead.
        if not a.party and not a.rounds and not a.disconnect:
            contents=[log.read_text(errors='replace') for _,_,_,log in jobs]
            samples=[re.findall(r'frame (\d+), confirmed (\d+),',s) for s in contents]
            if all(rows and int(rows[-1][1])>=max(600,a.frames) for rows in samples) and all(all(marker in s for marker in expected.get(a.case,[])) for s in contents):
                completed=True;break
        if a.rejoin:party_done=party_done and rejoined
        if party_done and a.case==10:party_done=all((name=='host' or 'PASS 2510' in log.read_text(errors='replace')) and 'frame 2400,' in log.read_text(errors='replace') for name,_,_,log in jobs)
        if party_done and a.case==12:party_done=all((name=='host' or 'PASS 2512' in log.read_text(errors='replace')) and 'frame 1800,' in log.read_text(errors='replace') for name,_,_,log in jobs)
        if party_done and (a.late_join or a.rejoin):
            caught=re.findall(r'caught up to practice frame (\d+)',jobs[0][3].read_text(errors='replace'))
            party_done=bool(caught) and all(max(map(int,re.findall(r'frame (\d+),',log.read_text(errors='replace')) or ['0']))>int(caught[-1])+600 for name,_,_,log in jobs if not(a.rejoin and name=='guest'))
        if party_done:completed=True;break
        if a.rounds and all(return_complete(log.read_text(errors='replace')) for name,_,_,log in jobs if not(a.join_in_match and name=='player2')):
            if not a.join_in_match or 'frame 600,' in jobs[-1][3].read_text(errors='replace'):completed=True;break
        if a.disconnect and not disconnected and all('frame 600,' in log.read_text(errors='replace') for _,_,_,log in jobs):
            victim=next(proc for name,proc,_,_ in jobs if name==a.disconnect);victim.terminate();disconnected=True;disconnect_at=time.time()
        if disconnected and a.disconnect=='watch0' and time.time()-disconnect_at>8:
            assert all(proc.poll() is None for name,proc,_,_ in jobs if name!='watch0'), 'Spectator departure stopped a player'
            completed=True;break
        if disconnected and a.party and a.disconnect!='host' and all('frame 1800,' in log.read_text(errors='replace') for name,_,_,log in jobs if name!=a.disconnect):completed=True;break
        if a.kick and all('frame 1800,' in log.read_text(errors='replace') for name,_,_,log in jobs if name!='guest') and next(proc for name,proc,_,_ in jobs if name=='guest').poll() is not None:completed=True;break
        time.sleep(.2)
finally:
    if watched:
        print('TIMELINE (seconds after the first client started'+('; the freeze was at %.1f'%(frozen_at-began) if frozen_at else '')+')',flush=True)
        for at,name,line in timeline:print('  %7.1f%s  %-8s %s'%(at-began,' (+%.1f)'%(at-frozen_at) if frozen_at and at>=frozen_at else '',name,line),flush=True)
        for name,_,_,log in jobs:
            if log.exists():print('  CONFIRMED %-8s %d at the trigger, %d at the end'%(name,base.get(name,0),confirmed_blank(name,log.read_text(errors='replace'))),flush=True)
    for name,proc,f,log in jobs:
        timed=proc.poll() is None;used[name]=(cpu_seconds(proc),time.time()-started[name])
        if timed and not completed:print('HARNESS DEADLINE:',name,flush=True)
        if timed:proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill();proc.wait(timeout=10)
        f.close()
        print(name,proc.returncode,'ROUNDS COMPLETE' if completed else 'TIMEOUT' if timed else '',flush=True)
        print('\n'.join(l for l in log.read_text(errors='replace').splitlines() if not l.startswith('audit'))[-3000:],flush=True)
    if proxy:
        proxy.terminate()
        try:proxy.wait(timeout=10)
        except subprocess.TimeoutExpired:proxy.kill();proxy.wait(timeout=10)
        proxy_log.close();print((out/'proxy.log').read_text(errors='replace')[-1500:],flush=True)
    for name,_,_,log in jobs:
        line=summary(name,log.read_text(errors='replace'))
        if line:print(line,flush=True)
        if used.get(name,(None,0))[0] is not None:print('CPU %-8s %.1f s of processor time in %.1f s'%(name,used[name][0],used[name][1]),flush=True)

# A zero exit alone is not a pass: a cleanly reported disconnect/desync also exits zero.
plans={};winners={}
for name,proc,_,log in jobs:
    content=log.read_text(errors='replace')
    if a.shots:
        assert completed and 'FAIL' not in content and 'went out of sync' not in content,(log,'the pictures were not all written')
        if any(item.split(':')[0]==name for item in a.shots):
            assert 'bt3: sound: dummy' in content or 'bt3: sound:' not in content,(log,'a rendered client opened a real sound device')
        continue
    if a.bad_teams:
        assert 'FAIL' not in content and 'went out of sync' not in content,log
        if name=='host':assert re.search(r'tagnet: %d teams'%a.teams,content) is None and 'Choose teams.' in content,(log,'the host did not stay on its setup page')
        else:
            assert 'The room contains unsupported fighters, outfits or rules.' in content,(log,'the guest accepted a room with an empty team')
            assert 'teams, by setup slot' not in content,(log,'the guest started a match')
            print('REFUSED',name,'The room contains unsupported fighters, outfits or rules.',flush=True)
        continue
    if a.differ or a.team_differ:
        # N4: the match stops on every copy; the copy that was made to differ and the host (or, when the host
        # differs, the host and the first guest) each leave a report holding both sides' records.
        # (The host of a practice lobby has no world: there the two reports are the two guests'.)
        other='guest' if differ.split(':')[0]=='host' else 'player2' if a.party and not a.rounds else 'host'
        assert 'FAIL' not in content and 'went out of sync' in content,(log,'did not stop for the difference')
        report=settings_file(name).parent/'tagnet-report.txt'
        if name in (differ.split(':')[0],other):
            assert 'mismatch report written to' in content and '(both copies)' in content,(log,'no report with both copies')
            assert 'A report was saved' in content,(log,'the message does not say where the report is')
            text=report.read_text(errors='replace')
            # (copies that disagree about the teams differ from the first compared blank on: there is no agreed one)
            assert 'First differing blank' in text and ('Last agreed blank' in text or a.team_differ) and 'Build identity' in text,(report,'incomplete')
            if a.differ:assert re.search(r'differs: .*\bhp\b',text),(report,'the differing health is not shown')
            else:
                assert re.search(r'differs: .*\bteam\b',text),(report,'the differing team is not shown')
                print('REPORT',name,[l.strip() for l in text.splitlines() if l.startswith('Teams:') or l.startswith('First differing') or 'differs: ' in l][:4],flush=True)
            assert text.count('this copy ')>=4 and text.count('other copy ')>=4,(report,'a side is missing')
            print('REPORT',name,report,len(text.splitlines()),'lines',flush=True)
        continue
    assert 'FAIL' not in content and 'divergence' not in content and 'went out of sync' not in content, log
    speeds=list(map(int,re.findall(r'rewinds \d+, speed (\d+)%',content)))
    if speeds:assert set(speeds)=={a.host_speed},(log,speeds,a.host_speed)
    for wanted in a.expect:
        if wanted.split(':',1)[0]==name:assert wanted.split(':',1)[1] in content,(log,wanted)
    for unwanted in a.reject:
        if unwanted.split(':',1)[0]==name:assert unwanted.split(':',1)[1] not in content,(log,unwanted)
    if a.teams and a.teams>=3 and a.rounds:
        # Three to five teams: every copy starts each match from the same table of teams and owners, and
        # every copy that reaches the result names the same winning team.
        plans[name]=re.findall(r'tagnet: (\d teams, by setup slot: .*)',content)
        assert len(plans[name])>=a.rounds and all(p.startswith(str(a.teams)) for p in plans[name]),(log,'no match of %d teams'%a.teams,plans[name])
        if name not in victims:
            winners[name]=decided(final.get(name,content) if watched else content)
            assert len(winners[name])==a.rounds,(log,'the match was not decided',winners[name])
    if watched:
        if name in victims or a.freeze=='host':continue
        # What a client says while the harness closes the room afterwards is not part of the check.
        content=final.get(name,content)
        assert not any(s in content for s in STOPPED),(log,'the match stopped')
        assert 'unsupported fighters' not in content,log
        gained=confirmed_blank(name,content)-base.get(name,0)
        assert gained>=a.frames,(log,'confirmed only %d more blanks'%gained)
        assert not a.then_return or back_in_practice(name,content),(log,'did not return to practice')
        continue
    if name==a.disconnect or (a.rejoin and name=='guest'):continue
    if a.kick and name=='guest':
        assert 'The host removed you from the lobby.' in content and 'PASS 2600' in content and proc.returncode==0,log
        continue
    if a.join_in_match and name=='player2':
        assert 'A match is in progress.' in content and 'frame 600,' in content, log
        continue
    if a.rounds:
        assert return_complete(content), log
        for marker in expected.get(a.case,[]):
            if a.party and name=='host' and marker=='PASS 2500':continue
            assert marker in content, (log,marker)
    elif a.disconnect and a.party and a.disconnect!='host':assert 'frame 1800,' in content, log
    elif a.disconnect and a.disconnect!='watch0':assert any(s in content for s in STOPPED), log
    elif not a.disconnect:
        assert 'frame 600,' in content, log
        for marker in expected.get(a.case,[]):
            if a.party and name=='host' and marker in ('PASS 2510','PASS 2512'):continue
            assert marker in content, (log,marker)
        if a.lag and a.input and not name.startswith('watch') and not(name=='host' and (a.host_spectator or a.party)):
            assert any(int(v)>0 for v in re.findall(r'rewinds (\d+)',content)), log
    assert proc.returncode==0 or completed or name==a.disconnect, (log,proc.returncode)
    if a.party and name=='host':
        assert 'host remains on native mode menu; no practice battle loaded' in content,log
        first_practice=content.split('host remains on native mode menu; no practice battle loaded',1)[1].split('Choose teams.',1)[0]
        assert 'tagstage: scale=' not in first_practice, 'Host loaded the practice stage'
    if a.disconnect=='host':assert 'PASS 2600' in content,log
if plans:
    assert len(set(tuple(v[:a.rounds]) for v in plans.values()))==1,('the copies do not agree on the teams',plans)
    assert len(set(tuple(v) for v in winners.values()))==1,('the copies do not agree on the winner',winners)
    for line in next(iter(plans.values()))[:a.rounds]:print('TEAMS',line,flush=True)
    print('WINNER',' / '.join(next(iter(winners.values()))),'on',', '.join(sorted(winners)),flush=True)
if a.disconnect:assert disconnected, 'Disconnect point was not reached'
if a.freeze:assert frozen_at, 'Freeze point was not reached'
print('PASS: room clients completed the requested checks',flush=True)
