"""Free For All spawn spacing, terrain safety and rematch determinism.

--teams 2,2,2 checks a Team Battle of three to five teams instead: every team starts around its own base
(teammates together, teams apart), on dry ground inside the arena, and a rematch gives the same places."""
import argparse
import os
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2]
PROBE=re.compile(r"tagspawn tick=(\d+) actor=(\d+) pos=([-\d.]+),([-\d.]+),([-\d.]+)")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    # Native stage id 35 is the menu's Random entry, not a playable map.
    p.add_argument("--stage",type=int,choices=range(35),action="append")
    p.add_argument("--size",choices=range(2,11),type=int,default=10)
    p.add_argument("--scale",choices=(100,200,300),type=int,default=100)
    p.add_argument("--renderer",choices=("none","gpu"),default="none")
    p.add_argument("--shot",type=int,default=0)
    p.add_argument("--teams",help="Fighters per team of a Team Battle, for example 2,2,2")
    p.add_argument("--exe",default="port/build/bt3.exe" if os.name=="nt" else "port/build/bt3_64")
    p.add_argument("--data",help="Game data folder (BT3_DATA); default: gamedata in the tree")
    args=p.parse_args()
    exe=Path(args.exe)
    if not exe.is_absolute():exe=ROOT/exe
    if args.teams:args.size=sum(int(n) for n in args.teams.split(","))
    label=f"teams{args.teams.replace(',','-')}" if args.teams else str(args.size)
    failures=[]
    for stage in args.stage or range(35):
        out=ROOT/"port/build/tag-spawn-tests"/f"{stage}-{label}-{args.scale}"
        out.mkdir(parents=True,exist_ok=True)
        settings=out/"settings.txt";settings.write_text(f"tag_extra_intros=0\ntag_map_size={args.scale}\n")
        env={k:v for k,v in os.environ.items() if not k.startswith("BT3_")}
        size=args.size//2
        env.update(BT3_GS=args.renderer,BT3_DEMO="1",BT3_TAG_TEAM="1",BT3_TAG_PLAY=str(min(args.size,4)),
                   BT3_TAG_ROSTER=f"{size},{args.size-size}",BT3_TAG_TEST_STAGE="1",BT3_TAG_TEST_SPAWN="1",
                   BT3_TEST_STAGE=str(stage),BT3_SETTINGS=str(settings),BT3_SAVES=str(out/"saves"),
                   SDL_AUDIO_DRIVER="dummy",BT3_UPDATE_CHECK="0")
        if args.data:env["BT3_DATA"]=str(Path(args.data).resolve())
        if args.teams:env["BT3_TAG_TEAMS"]=args.teams
        if args.shot:
            shot=(out/"frame.ppm").relative_to(ROOT).as_posix()
            env.update(BT3_UI_SHOT=f"{args.shot}:{shot}",BT3_WINDOW="960x720")
        log=out/"runtime.log"
        with log.open("w") as f:
            r=subprocess.run([str(exe)],cwd=ROOT,env=env,
                             stdout=f,stderr=subprocess.STDOUT,timeout=90)
        text=log.read_text(errors="replace")
        if r.returncode!=0 or "PASS check=99" not in text:
            failures.append(str(log));print(f"FAIL stage {stage}: {log}",flush=True);continue
        first={a:(x,y,z) for tick,a,x,y,z in PROBE.findall(text) if tick=="1"}
        again={a:(x,y,z) for tick,a,x,y,z in PROBE.findall(text) if tick=="40"}
        assert len(first)==args.size and first==again,(first,again)
        if args.teams:print(f"PASS stage {stage}: teams {args.teams} start together, apart, dry and inside at {args.scale}%",flush=True)
        else:print(f"PASS stage {stage}: {args.size} FFA spawns at {args.scale}%",flush=True)
    assert not failures,"\n".join(failures)
if __name__=="__main__":main()
