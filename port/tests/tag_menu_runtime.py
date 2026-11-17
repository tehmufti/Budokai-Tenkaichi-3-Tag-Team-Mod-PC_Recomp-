"""Exercise the native mod menus with real disc assets and scripted pad input.

No prepared matches or emulator states. Saves and settings belong to this test.
Run from the repository root with --case settings, back, or match.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    "settings": {
        "pad": "150:select,180:down,210:down,240:down,270:down,300:down,320:down,380:cross,440:cross,500:down,560:right,680:triangle,740:triangle,800:select",
        "end": r"frame=\d+ page=4 state=0,0,1,3,0",
        "after": 800,
        "states": [(4, 4), (4, 5), (4, 1), (4, 0)],
    },
    "back": {
        "pad": "150:select,210:cross,270:down,310:down,350:cross,530:start,650:triangle,800:triangle,860:triangle,920:triangle",
        "end": r"frame=\d+ page=4 state=0,0,1,3,0",
        "after": 920,
        "states": [(4, 2), (4, 3), (40, 0), (4, 3), (4, 2), (4, 1), (4, 0)],
    },
    "match": {
        "pad": "150:select,210:cross,270:cross,450:start,540:cross,600:cross,660:cross,720:cross,780:right,840:cross,900:cross,960:cross,1020:cross,1080:cross,1140:cross,1200:cross,1260:cross,1320:right,1380:cross,1440:cross,1500:cross,1560:cross,1700:cross",
        "end": r"tagintro actor=3 .*state=1",
        "after": 0,
        "states": [(4, 1), (4, 2), (4, 3), (40, 0), (40, 1)],
    },
}
def roster_pad(left=2,right=2,duplicates=False,cpu_only=False,cpu_steps=0):
    events=["150:select","210:cross","270:cross","450:start"]
    tick=540
    first_cpu=True
    def press(key):
        nonlocal tick
        events.append(f"{tick}:{key}")
        tick+=60
    for side,count in enumerate((left,right)):
        for member in range(count):
            if member:
                press("cross")  # open next free slot
                for _ in range(0 if duplicates else (0,1,2,4,5)[member]): press("right")
            # Side 2 starts one column to the right (Kid Gohan). Its third
            # and fifth choices open Vegeta/Trunks's form picker first.
            for _ in range(4 if not duplicates and side==1 and member in (2,4) else 3):
                press("cross") # fighter, optional form, equipment, colour
            if cpu_only or side!=0 or member!=0:
                for _ in range(cpu_steps if first_cpu else 0): press("down")
                press("cross") # CPU difficulty
                first_cpu=False
        if count<5: press("right") # End is optional, not forced after two
        press("cross")
    tick+=80
    press("cross") # stage
    return ",".join(events)

def bt4_roster_pad(left=2,right=2,cpu_only=False,cpu_steps=0):
    # Both first BT4 grid cells have a form picker. Repeated fighters also
    # exercise the native mod's duplicate-selection rule.
    events=["150:select","210:cross","270:cross","450:start"];tick=540
    first_cpu=True
    for side,count in enumerate((left,right)):
        for member in range(count):
            for _ in range(4+(member>0)):
                events.append(f"{tick}:cross");tick+=60
            if cpu_only or side!=0 or member!=0:
                for key in ['down']*(cpu_steps if first_cpu else 0)+['cross']:
                    events.append(f"{tick}:{key}");tick+=60
                first_cpu=False
        for key in (('right','cross') if count<5 else ('cross',)):
            events.append(f"{tick}:{key}");tick+=60
    tick+=80;events.append(f"{tick}:cross")
    return ','.join(events)

def adapt_bt4_roster(pad, sizes, duplicates=False,cpu_only=False,cpu_steps=0):
    """Replace only character selection, keeping mode/setup and later inputs.

    CPU-only selection starts later; return/result cases have later actions
    which must move by the same duration as BT4's extra form confirmations.
    """
    def parse(value):
        return [(int(t),key) for t,key in (event.split(':',1) for event in value.split(',') if event)]
    events=parse(pad)
    before=parse(roster_pad(*sizes,duplicates=duplicates,cpu_only=cpu_only,cpu_steps=cpu_steps))[4:]
    after=parse(bt4_roster_pad(*sizes,cpu_only=cpu_only,cpu_steps=cpu_steps))[4:]
    for start in range(len(events)-len(before)+1):
        offset=events[start][0]-before[0][0]
        if events[start:start+len(before)]==[(t+offset,k) for t,k in before]:
            delta=after[-1][0]-before[-1][0]
            events=(events[:start]+[(t+offset,k) for t,k in after]+
                    [(t+delta,k) for t,k in events[start+len(before):]])
            return ','.join(f'{t}:{k}' for t,k in events)
    return pad
CASES["match"]["pad"]=roster_pad()
CASES["camera-views"] = {
    "pad": "150:select,180:down,210:down,240:down,270:down,300:down,330:down,350:cross,"
           "410:down,450:down,490:down,550:cross,"
           "610:down,650:down,690:down,750:left,850:triangle,910:triangle,970:select",
    "end": r"frame=\d+ page=4 state=0,0,1,3,0",
    "after":970, "states":[(4,4),(4,8),(4,4),(4,1),(4,0)],
}
CASES["revival-ring"] = {
    "pad": "150:select,180:down,210:down,240:down,270:down,300:down,330:down,350:cross,410:cross,"
           "470:down,510:down,550:down,590:down,630:down,670:down,710:down,770:right,"
           "830:down,890:right,1010:triangle,1070:triangle,1130:select",
    "end": r"frame=\d+ page=4 state=0,0,1,3,0",
    "after":1130,"states":[(4,4),(4,5),(4,4),(4,1),(4,0)],
    "env":{"BT3_UI_SHOT":"950:port/build/tag-menu-tests/revival-ring/menu.ppm"},
}
CASES["fusion-settings"] = {
    # The last group and its Back row use the native second label sheet.
    "pad": "150:select,180:down,210:down,240:down,270:down,300:down,330:down,350:cross,"
           "410:down,450:down,490:down,530:down,570:down,610:down,650:down,710:cross,"
           "770:down,810:down,850:down,890:down,930:down,990:right,"
           "1050:down,1090:down,1130:down,1190:cross,1250:up,1310:cross,1370:select",
    "end": r"frame=\d+ page=4 state=0,0,1,3,0",
    "after":1370,"states":[(4,4),(4,12),(4,4),(4,1),(4,0)],
    "env":{"BT3_UI_SHOT":"1150:port/build/tag-menu-tests/fusion-settings/menu.ppm"},
}
CASES["stage-settings"] = {
    "pad": "150:select,180:down,210:down,240:down,270:down,300:down,330:down,350:cross,"+
           ",".join(f"{410+i*40}:down" for i in range(10))+
           ",830:cross,890:down,950:cross,1010:right,1070:down,1130:cross,1190:triangle,1250:select",
    "end": r"frame=\d+ page=4 state=0,0,1,3,0",
    "after":1250,"states":[(4,4),(4,15),(4,4),(4,1),(4,0)],
    "env":{"BT3_UI_SHOT":"1040:port/build/tag-menu-tests/stage-settings/menu.ppm"},
}
CASES["team-layout"] = {
    "pad": "150:select,210:cross,270:down,310:down,350:down,390:cross,"
           "450:cross,510:right,570:cross,630:down,690:cross,750:left,810:cross,870:start,1040:triangle",
    "end": r"frame=\d+ page=4 state=3,0,0,0,0",
    "after":1040,"states":[(4,3),(45,1),(40,0),(4,3)],
    "assignments":[(1,1,0,1,4),(1,0,0,1,4)],
}
CASES["control-bindings"] = {
    "pad":"150:select,180:down,210:down,240:down,270:down,300:down,330:down,350:cross,"
          +",".join(f"{410+i*30}:down" for i in range(10))+
          ",730:cross,790:down,830:down,870:down,950:cross,1010:down,1070:right,"+
          ",".join(f"{1150+i*60}:down" for i in range(8))+
          ",1690:right,1810:triangle,1870:triangle,1930:l3",
    "end":r"frame=\d+ page=4 state=0,0,1,3,0",
    "after":1930,"states":[(4,4),(4,17),(4,4),(4,1),(4,0)],
    "env":{"BT3_UI_SHOT":"1740:port/build/tag-menu-tests/controls-menu.ppm"},
}
CASES["settings-pagination"] = {
    "pad":"150:select,180:down,210:down,240:down,270:down,300:down,330:down,350:cross,"
          +",".join(f"{410+i*30}:down" for i in range(10))+
          ",730:cross,790:down,830:down,870:cross,"+
          ",".join(f"{930+i*30}:down" for i in range(10))+
          ",1250:cross,"+",".join(f"{1310+i*30}:down" for i in range(8))+
          ",1570:right,1630:triangle,1690:triangle,1750:select",
    "end":r"frame=\d+ page=4 state=0,0,1,3,0",
    "after":1750,"states":[(4,4),(4,16),(4,4),(4,1),(4,0)],
}
CASES["cpu-swap"] = {
    "pad":"150:select,210:cross,270:cross,330:cross,390:right,450:cross,510:start,670:triangle",
    "end":r"frame=\d+ page=4 state=3,0,0,0,0",
    "after":670,"states":[(4,3),(45,1),(40,0),(4,3)],
    "assignments":[(1,0,0,0,1)],
}
CASES["unequal"] = dict(CASES["match"],pad=roster_pad(4,2),end=r"tagintro actor=5 .*state=1",roster=(4,2))
CASES["full-roster"] = dict(CASES["match"],pad=roster_pad(5,5),end=r"tagintro actor=9 .*state=1",roster=(5,5))
CASES["duplicates"] = dict(CASES["match"],pad=roster_pad(3,2,True),end=r"tagintro actor=4 .*state=1",roster=(3,2))
CASES["cpu-label"] = {
    "pad":"150:select,210:cross,270:down,310:down,350:down,390:down,650:cross",
    "end":r"frame=\d+ page=4 state=3,0,0,0,0","after":650,
    "states":[(4,2),(4,3)],"env":{"BT3_UI_SHOT":"500:port/build/tag-menu-tests/cpu-label/menu.ppm"},
}
CASES["setup-edit-cancel"] = {
    # Only the timer is shown here. Triangle cancels its edit; Cross saves.
    "pad":"150:select,210:cross,270:down,310:down,350:down,390:down,450:cross,"
          "510:cross,570:right,630:triangle,690:cross,750:right,810:cross,930:triangle",
    "end":r"frame=\d+ page=4 state=2,","after":930,
    "states":[(4,3),(4,2)],
    "env":{"BT3_UI_SHOT":"900:port/build/tag-menu-tests/setup-edit-cancel/menu.ppm"},
}
for mode, navigation in (("free-for-all", "180:down,"), ("training", "175:down,195:down,")):
    CASES[mode] = dict(CASES["match"], pad=CASES["match"]["pad"].replace("210:cross", navigation + "210:cross"))
for mode, navigation, mode_id in (("team", "", 0), ("free-for-all", "180:down,", 1), ("training", "175:down,195:down,", 2)):
    # Set the timer here, and each CPU's difficulty after their outfit.
    pad="150:select,"+navigation+"210:cross,270:down,310:down,350:down,390:down,450:cross,"
    pad+="510:cross,"+("550:right," if mode=="training" else "550:right,590:right,")
    pad+="630:cross,690:start"
    for event in roster_pad(cpu_only=True,cpu_steps=2).split(",")[4:]:
        tick,key=event.split(":");pad+=f",{int(tick)+330}:{key}"
    CASES["cpu-"+mode] = dict(CASES["match"],pad=pad,
        end=r"tagteam frame=150 fighter=3",cpu=True,mode_id=mode_id,cpu_steps=2,
        env={"BT3_TAG_DEBUG":"1","BT3_BGM_DEBUG":"1"})
CASES["pause"] = {
    "pad": "", "after": 0, "end": r"page=91 state=3,0,",
    "states": [(90, 2), (91, 2), (90, 3), (91, 3)],
    "env": {"BT3_DEMO": "1", "BT3_TAG_PLAY": "4", "BT3_TAG_ROSTER": "2,2", "BT3_TAG_INPUT_TRACE": "1",
            "BT3_UI_SHOT": "1100:port/build/tag-menu-tests/pause/menu.ppm",
            "BT3_PAD_3": "900:start,960:down,1020:cross,1140:triangle,1200:start",
            # The native pause menu remembers the selected Skill List row.
            "BT3_PAD_4": "1260:start,1380:cross,1500:triangle,1560:start"},
}
for destination, downs, page, state in (("characters", "", 40, 0), ("main", "3830:down,", 4, 1)):
    CASES["return-" + destination] = {
        # Wait for all four voiced entrances and Ready/Fight before pausing.
        "pad": CASES["match"]["pad"] + ",3700:start,3760:down,3800:down," + downs + "3860:cross,3920:up,3980:cross",
        "end": rf"frame=\d+ page={page} state={state},",
        "after": 3700,
        "states": CASES["match"]["states"] + [(90, 0), (page, state)],
    }


for loss in (False, True):
    for destination,downs,page,state in (
        ("retry","",92,4),("characters","4140:down,",40,0),
        ("main","4100:down,4140:down,",4,1)):
        CASES[("loss-" if loss else "win-")+destination]={
            "pad":roster_pad()+","+downs+"4200:cross,4300:up,4400:cross",
            "end":rf"frame=\d+ page={page} state={state},","after":4200,
            "states":CASES["match"]["states"]+[(90,0),(page,state)],
            "settings":"tag_extra_intros=0\n",
            "env":{"BT3_TAG_TEST_RESULT":"2" if loss else "1","BT3_UNCAPPED":"1"},
        }


# ---- Team Battle with three to five teams ------------------------------------------------------------------------
# Team Battle asks "How many teams?" before Players. The older Team Battle cases answer "2 Teams" at frame 240,
# between two of their own presses, so everything after it happens at the frame it always did.
TEAMS_PAGE=101
def team_route(pad):
    head="150:select,210:cross,"
    return head+"240:cross,"+pad[len(head):] if pad.startswith(head) else pad

# The one older route that is longer now: Players' Back leads to the teams page, and that one to Modded Modes.
CASES["back"]=dict(CASES["back"],pad=CASES["back"]["pad"]+",980:triangle",after=980,
    states=[(4,2),(4,3),(40,0),(4,3),(4,2),(4,TEAMS_PAGE),(4,1),(4,0)])


class Script:
    """Presses of up to four pads on one clock (the game holds every press for four frames)."""
    def __init__(self,start=150):
        self.t=start;self.events={1:[],2:[],3:[],4:[]};self.shots={}
    def press(self,key,gap=60,pad=1,times=1):
        for _ in range(times):
            self.events[pad].append(f"{self.t}:{key}");self.t+=gap
        return self
    def wait(self,frames):
        self.t+=frames;return self
    def shot(self,label):
        """A picture just before the next press (taken with --shots)."""
        self.shots[self.t-6]=label;return self
    def env(self):
        keys={1:"BT3_PAD",2:"BT3_PAD_2",3:"BT3_PAD_3",4:"BT3_PAD_4"}
        return {keys[n]:",".join(e) for n,e in self.events.items() if e}


def squad_setup(teams,players):
    """Modded Modes > Team Battle > <teams> Teams > <players> players (0: CPU Only): TEAM SETUP is open."""
    s=Script().press("select").press("cross",30)
    s.press("down",20,times=teams-2).wait(10).press("cross",30)
    return s.press("down",20,times=4 if players==0 else players-1).wait(10).press("cross",90)

def squad_edit(s,moves,change):
    """TEAM SETUP: `moves` (directions) bring the focus to a card; Cross edits it, `change` presses right (left
    when negative), Cross saves."""
    for key in moves.split(): s.press(key,30)
    return s.press("cross",30).press("right" if change>0 else "left",30,times=abs(change)).press("cross",30)

def squad_pick(s,rows,owners,bt4):
    """Character select with planned rows: another fighter in every slot. owners[row][slot] is the pad that picks
    it (None: a CPU's slot, picked by pad 1, with the difficulty prompt). The cursor is on End by itself once
    the row is full, so End is one Cross."""
    for r,count in enumerate(rows):
        for m in range(count):
            pad=owners[r][m] or 1
            if m:
                s.press("cross",60,pad)                      # open the next free slot
                if not bt4: s.press("right",60,pad,times=(0,1,2,4,5)[m])
            # (row 2 starts one column to the right: its third and fifth fighters open the form picker first;
            #  on BT4 the first grid cell always has one, and the same fighter may be picked again)
            s.press("cross",60,pad,times=4 if bt4 or (r==1 and m in (2,4)) else 3)
            if owners[r][m] is None: s.press("cross",60)     # CPU difficulty
            s.shot(f"selector-row{r+1}-slot{m+1}")
        s.press("cross",60)                                  # End
    return s.wait(20).press("cross",60)                      # the stage

def squad_layout(size):
    """include/battle/tag_squad.h once more: the two rows of team numbers, and the team of every fighter of the
    match (fighters are numbered across the rows: slot 1 of row 1, slot 1 of row 2, slot 2 of row 1, ...)."""
    import itertools
    teams,total,best,split,head=len(size),sum(size),None,None,0
    for n in range(1,teams+1):
        for row0 in itertools.combinations(range(teams),n):
            a=sum(size[t] for t in row0)
            if row0[0]!=0 or a>5 or not 1<=total-a<=5: continue
            key=(abs(2*a-total),list(row0))
            if best is None or key<best: best=key
    if best is None:
        for s in range(teams-1,0,-1):
            for n in range(1,teams):
                for row0 in itertools.combinations([t for t in range(teams) if t!=s],n):
                    k=5-sum(size[t] for t in row0)
                    if row0[0]!=0 or not 1<=k<=size[s]-1: continue
                    if best is None or list(row0)<best[1]: best,head=(0,list(row0)),k
            if best is not None:
                split=s;break
    rows=[[],[]]
    for t in range(teams):
        if t!=split: rows[0 if t in best[1] else 1]+=[t]*size[t]
    if split is not None:
        rows[0]+=[split]*head;rows[1]+=[split]*(size[split]-head)
    return rows,[rows[r][m] for m in range(5) for r in range(2) if m<len(rows[r])]

def squad_owners(rows,player_team):
    """Players take the first fighters of their team, row 1 before row 2 (pads 1..4 here; None is a CPU)."""
    owners=[[None]*len(row) for row in rows]
    for p,team in enumerate(player_team):
        r,m=next((r,m) for r in range(2) for m in range(len(rows[r])) if rows[r][m]==team and owners[r][m] is None)
        owners[r][m]=p+1
    return owners

def squad_result(s,row):
    """The result menu of a match BT3_TAG_TEST_RESULT has ended: Fight Again, Character Select or Main Menu
    (row 0..2), then Yes."""
    s.wait(2200).shot("result").press("down",40,times=row).wait(100-40*row).press("cross",100).press("up",100)
    return s.press("cross",100)

def squad_case(size,player_team,setup=None,then=None,settings="",env=None,**more):
    """A match of len(size) teams from the menus. `setup` edits TEAM SETUP: it must leave the sizes `size` and
    the players on the teams `player_team`; `then` goes on once the stage is chosen."""
    rows,teams=squad_layout(list(size))
    owners=squad_owners(rows,player_team)
    def build(bt4):
        s=squad_setup(len(size),len(player_team))
        if setup: setup(s)
        s.wait(30).shot("setup").press("start",150)
        squad_pick(s,[len(rows[0]),len(rows[1])],owners,bt4)
        if then: then(s,bt4)
        return s
    case=dict(build=build,squad=tuple(size),players=tuple(player_team),rows=rows,teams=teams,owners=owners,fights=1,
              end=rf"tagteam frame=150 fighter={len(teams)-1} ",after=0,
              states=[(4,1),(4,TEAMS_PAGE),(4,2),(4,3),(40,0),(40,1)],settings="tag_extra_intros=0\n"+settings,
              env=dict({"BT3_TAG_DEBUG":"1","BT3_UNCAPPED":"1"},**(env or {})))
    case.update(more)
    return case

def check_squad(spec,text):
    size,rows,teams,owners=spec["squad"],spec["rows"],spec["teams"],spec["owners"]
    # what TEAM SETUP left in the session when the match was set up (page 46): the teams, their fighters, the two
    # rows, the players' teams
    before=text.split("page=46 state=")[0]
    plans=[tuple(map(int,m.split(","))) for m in re.findall(r"page=44 state=([\d,]+)",before)]
    packed=int("".join(str(size[t]) if t<len(size) else "0" for t in range(5)))
    assert plans and plans[-1]==(len(size),packed,len(rows[0]),len(rows[1]),len(spec["players"])),plans
    seats=[tuple(map(int,m.split(","))) for m in re.findall(r"page=45 state=([\d,]+)",before)]
    now=seats[-1][:len(spec["players"])] if seats else tuple(p%len(size) for p in range(len(spec["players"])))
    assert now==spec["players"],seats
    # the markers above the slots of the character select: team and owner of every slot
    marks={}
    for side,member,mark in re.findall(r"page=41 state=(\d),(\d),(\d+),",text):
        if int(mark): marks[(int(side),int(member))]=int(mark)
    want={(r,m):1+(owners[r][m] or 0)+10*(rows[r][m]+1) for r in range(2) for m in range(len(rows[r]))}
    assert marks==want,(marks,want)
    # hand-over: the pad that picks goes to every player who owns a slot (pad 1 picks for the CPUs)
    selectors={int(n) for n in re.findall(r"page=40 state=\d+,\d+,-?\d+,\d+,(\d+)",text)}
    assert selectors=={0}|set(range(len(spec["players"]))),selectors
    # what the match was given: fighter, owner (-1 a CPU), team
    slots=[(r,m) for m in range(5) for r in range(2) if m<len(rows[r])]
    assigned={int(a):(int(o),int(t)) for a,o,t in re.findall(r"page=42 state=(\d+),(-?\d+),(\d+),",text)}
    assert assigned=={a:((owners[r][m] or 0)-1,rows[r][m]) for a,(r,m) in enumerate(slots)},assigned
    # every fight: each fighter on its planned team; until the decision the players' fighters are theirs and
    # everybody else is a CPU
    fights=[]
    for actor,team in re.findall(r"tagteam frame=150 fighter=(\d+) chara=\d+ team=(\d+)",text):
        if int(actor)==0: fights.append({})
        fights[-1][int(actor)]=int(team)
    assert len(fights)==spec["fights"] and all(f==dict(enumerate(teams)) for f in fights),(fights,teams)
    human={a for a,(r,m) in enumerate(slots) if owners[r][m]}
    controls={(int(a),c!="2") for a,c in re.findall(r"tagteam control fighter=(\d+) control=(\d+)",text.split("tagdecided")[0])}
    assert controls=={(a,a in human) for a in range(len(teams))},controls


CASES["teams3-match"]=squad_case((2,2,2),(0,))
CASES["teams5-cpu"]=squad_case((2,2,2,2,2),())
# Two players on one team of four: P2 leaves team 2 for team 1 (P2's card is the one to the right of P1's).
CASES["teams4-pair"]=squad_case((2,2,2,2),(0,0),setup=lambda s:squad_edit(s,"right",-1))

def uneven_setup(s):
    squad_edit(s,"up right",-1)      # team 2: one fighter
    squad_edit(s,"right",1)          # team 3: three fighters
    squad_edit(s,"down",2)           # P1: to team 2, then to team 3
# Teams of 2, 1 and 3 with the player on team 3, which the test switch lets win; then each row of the result menu.
def uneven_case(then,**more):
    return squad_case((2,1,3),(2,),setup=uneven_setup,env={"BT3_TAG_TEST_RESULT":"3"},then=then,timeout=200,**more)
# Fight Again: the same six fighters on the same teams once more.
CASES["teams3-retry"]=uneven_case(lambda s,bt4:squad_result(s,0),result=0,fights=2,end=r"page=92 state=6,\d+,0,2,3")
CASES["teams3-retry"]["states"]+=[(90,0),(92,6)]
def characters_again(s,bt4):
    """Character Select: the rows come back as they were played. End both, choose the stage, fight again."""
    squad_result(s,1)
    s.wait(200).shot("selector-again")
    for _ in range(2):
        # (a row opens on its first slot's grid: Triangle shows the row, Left goes to End)
        s.press("triangle",60).press("left",60).shot("selector-again-end").press("cross",90)
    return s.wait(20).press("cross",60)
CASES["teams3-characters"]=uneven_case(characters_again,result=1,fights=2,end=r"page=92 state=6,\d+,0,2,3")
CASES["teams3-characters"]["states"]+=[(90,0),(40,0),(40,1),(92,6)]
def main_again(s,bt4):
    """Main Menu: Modded Modes again. Team Battle with two teams, then with three: both start from nothing."""
    squad_result(s,2)
    s.wait(300).press("cross",30).press("cross",30).press("cross",90).shot("setup-two-teams-after")   # 2 Teams, One Player
    s.press("triangle").press("triangle").press("down",30).press("cross",30).press("cross",90).shot("setup-three-teams-after")
    return s.press("triangle").press("triangle").press("triangle").press("triangle")
CASES["teams3-main"]=uneven_case(main_again,result=2,end=r"frame=\d+ page=4 state=0,0,1,3,0",after="last",
    setups=[(3,22200,1,1000,0),(2,0,1,1000,0),(3,22200,1,1000,0)])
CASES["teams3-main"]["states"]+=[(90,0),(4,1),(4,TEAMS_PAGE),(4,2),(4,3),(4,2),(4,TEAMS_PAGE),(4,2),(4,3),(4,2),(4,TEAMS_PAGE),(4,1),(4,0)]

def teams_back(bt4):
    s=Script().press("select").press("cross")              # Modded Modes > Team Battle: the teams page
    s.shot("teams-page").press("triangle")                 # Triangle: Modded Modes
    s.press("cross").press("down",30,times=4).wait(30).shot("teams-page-back-row").press("cross")   # its Back row
    s.press("cross").press("down",30).wait(30).shot("teams-page-3").press("cross")                  # 3 Teams: Players
    s.shot("players").press("triangle")                    # Players' Triangle: the teams page again
    s.press("down",30,times=2).wait(30).press("cross")     # 4 Teams: Players
    s.press("down",30,times=5).wait(30).press("cross")     # Players' Back row: the teams page
    s.press("down",30,times=3).wait(30).press("cross")     # 5 Teams: Players
    s.press("cross",90).shot("setup-5-teams")              # One Player: TEAM SETUP with five columns
    squad_edit(s,"up right right",-1)                      # team 3: one fighter
    s.press("start",150).shot("selector")                  # the character select
    s.press("triangle",150).shot("setup-after-selector")   # back out: TEAM SETUP as it was left
    return s.press("triangle").press("triangle").press("triangle").press("triangle").shot("main-menu")
CASES["teams-back"]={"build":teams_back,"end":r"frame=\d+ page=4 state=0,0,1,3,0","after":"last",
    "states":[(4,1),(4,TEAMS_PAGE),(4,1),(4,TEAMS_PAGE),(4,1),(4,TEAMS_PAGE),(4,2),(4,TEAMS_PAGE),(4,2),(4,TEAMS_PAGE),
              (4,2),(4,3),(40,0),(4,3),(4,2),(4,TEAMS_PAGE),(4,1),(4,0)],
    "setups":[(5,22222,1,1000,0),(5,22122,1,1000,0)],"env":{"BT3_UNCAPPED":"1"}}

def teams_end(bt4):
    s=squad_setup(3,1).press("start",150)
    s.press("cross",60,times=4 if bt4 else 3)              # the player's fighter: one of the two the row needs
    s.press("left",60,times=2).shot("end-under-cursor")   # over the slot just filled to End
    s.press("cross",90).shot("end-refused")               # refused: the row is still open
    return s.press("right",60)                            # (the cursor goes on to the first slot)
# state=<row>,<6: the row's slots>,<5: End, then 0: the first slot>: the row never ended (no row 1 line at all)
CASES["teams-end"]={"build":teams_end,"end":r"frame=\d+ page=40 state=0,6,0,","after":"last",
    "states":[(4,TEAMS_PAGE),(4,2),(4,3),(40,0)],"env":{"BT3_UNCAPPED":"1"},"never":r"page=40 state=1,",
    "seen":r"page=40 state=0,6,5,"}

def teams_refuse(bt4):
    s=squad_setup(5,2)                                     # 2-2-2-2-2, P1 on team 1, P2 on team 2
    s.press("up",30).press("cross",30).press("right",30).wait(30).shot("ten-fighters")   # an eleventh fighter: refused
    s.press("triangle",30)                                 # (cancel)
    s.press("down",30).press("right",30).press("cross",30).press("left",30).press("cross",30)   # P2 joins P1 on team 1
    s.wait(30).shot("two-players-one-team")
    s.press("up",30).press("up",30).press("cross",30).press("left",30).wait(30).shot("needs-fighters")   # one fighter for two players: refused
    s.press("triangle",30)
    return s.press("triangle").press("triangle").press("triangle").press("triangle")
CASES["teams-refuse"]={"build":teams_refuse,"end":r"frame=\d+ page=4 state=0,0,1,3,0","after":"last",
    "states":[(4,TEAMS_PAGE),(4,2),(4,3),(4,2),(4,TEAMS_PAGE),(4,1),(4,0)],"env":{"BT3_UNCAPPED":"1"},
    # (notice, team) of the hint row: ten at most on team 1's card; team 1 needs a fighter for each of its two players
    "notices":[(1,1),(3,1)],"plan":(5,22222),"seats":(0,0)}

def teams_full(bt4):
    s=squad_setup(3,3)                                     # P1, P2, P3 on teams 1, 2, 3
    squad_edit(s,"up",-1)                                  # every team down to one fighter
    squad_edit(s,"right",-1)
    squad_edit(s,"right",-1)
    s.press("down",30).press("cross",30).press("right",30).wait(30).shot("no-team-left")   # P3: nowhere to go
    s.press("triangle",30)
    return s.press("triangle").press("triangle").press("triangle").press("triangle")
CASES["teams-full"]={"build":teams_full,"end":r"frame=\d+ page=4 state=0,0,1,3,0","after":"last",
    "states":[(4,TEAMS_PAGE),(4,2),(4,3),(4,2),(4,TEAMS_PAGE),(4,1),(4,0)],"env":{"BT3_UNCAPPED":"1"},
    "notices":[(2,1)],"plan":(3,11100),"seats":(0,1,2)}


def run(case, exe, renderer, data=None, lang="en", shots=False):
    spec = dict(CASES[case])
    if renderer=='none':
        raise ValueError('Scripted menu input requires --renderer gpu.')
    marker=Path(data)/'native-disc.json' if data else None
    bt4=bool(marker and marker.exists() and json.loads(marker.read_text()).get('game')=='bt4')
    pads,pictures={},{}
    if "build" in spec:
        script=spec["build"](bt4)
        pads=script.env();spec["pad"]=pads.pop("BT3_PAD");pictures=script.shots
        if spec["after"]=="last": spec["after"]=int(spec["pad"].split(",")[-1].split(":")[0])
    else:
        if bt4:
            sizes=spec.get('roster',(2,2))
            spec['pad']=adapt_bt4_roster(spec['pad'],sizes,case=='duplicates',spec.get('cpu',False),spec.get('cpu_steps',0))
        spec['pad']=team_route(spec['pad'])
    output = ROOT / "port/build/tag-menu-tests" / ((Path(data).name+"-" if data else "")+case+("" if lang=="en" else "-"+lang))
    output.mkdir(parents=True, exist_ok=True)
    settings = output / "settings.txt"
    # These cases exercise menu routing with scripted logical pads. Physical
    # controller check-in has its own SDL integration fixture.
    settings.write_text("tag_revive_seconds=3\ntag_controller_check=0\n"+spec.get("settings",""), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BT3_")}
    env.update(BT3_GS=renderer, BT3_TAG_TEAM="1", BT3_TAG_MENU_TEST="main",
               BT3_MENU_LANG=lang, BT3_UPDATE_CHECK="0", BT3_TAG_TRACE="1",
               BT3_LOAD_TRACE="1", BT3_SAVES=str(output / "saves"),
               BT3_SETTINGS=str(settings), BT3_MENU_ITEM4="0", BT3_PAD=spec["pad"],
               BT3_PACED="1", SDL_AUDIO_DRIVER="dummy")
    env.update(pads)
    env.update(spec.get("env", {}))
    for old in output.glob("*.ppm"): old.unlink()
    if shots and pictures:
        # <frame>.ppm in the case's folder; pictures.json says what each one shows
        env["BT3_UI_SHOTS"]=",".join(map(str,sorted(pictures)))+":"+str(output)+os.sep
        (output/"pictures.json").write_text(json.dumps({str(f):pictures[f] for f in sorted(pictures)},indent=1)+"\n")
    if data: env['BT3_DATA']=str(Path(data).resolve())
    if data: env.pop('BT3_PACED',None)
    if env.get("BT3_UNCAPPED") == "1":env.pop("BT3_PACED",None)
    if renderer=="none":env.pop("BT3_PACED",None)
    path = output / "runtime.log"
    with path.open("w", encoding="utf-8") as log:
        p = subprocess.Popen([str(exe)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + spec.get("timeout",120)
        try:
            while time.monotonic() < deadline:
                text = path.read_text(encoding="utf-8", errors="replace")
                assert "crashed:" not in text, f"Native crash: {path}"
                matches = list(re.finditer(spec["end"], text))
                if any(spec["after"] == 0 or int(re.search(r"frame=(\d+)", m[0])[1]) > spec["after"] for m in matches):
                    break
                assert p.poll() is None, f"Game exited before completion: {path}"
                time.sleep(0.1)
            else:
                raise AssertionError(f"Timed out: {path}")
        finally:
            if p.poll() is None:
                p.terminate()
            p.wait(timeout=10)
    transitions = [(int(a), int(b)) for a, b in re.findall(r"tagmenu frame=\d+ page=(\d+) state=(\d+),", text)]
    remaining = iter(transitions)
    for expected in spec["states"]:
        assert expected in remaining, f"Missing ordered transition {expected}: {path}"
    assert "page=80" not in text, "Standalone setup page was entered"
    assert "bt3: sound: dummy" in text, "The sound device is not the silent one"
    if "squad" in spec: check_squad(spec,text)
    assert "never" not in spec or not re.search(spec["never"],text), "Seen: "+spec.get("never","")
    assert "seen" not in spec or re.search(spec["seen"],text), "Not seen: "+spec.get("seen","")
    if "setups" in spec:
        # the draft TEAM SETUP opened with, every time: teams, fighters per team, players, their teams, mode
        opened=[tuple(map(int,m.split(","))) for m in re.findall(r"page=43 state=([\d,]+)",text)]
        assert opened==spec["setups"],opened
    if "notices" in spec:
        # refusals on TEAM SETUP in order, (notice, team) of the hint row while a card is edited; what is left
        said=[(int(n),int(t)) for n,t in re.findall(r"page=4 state=3,\d+,1,([1-9]),(\d)",text)]
        assert said==spec["notices"],said
        plans=[tuple(map(int,m.split(","))) for m in re.findall(r"page=44 state=([\d,]+)",text)]
        assert plans[-1][:2]==spec["plan"],plans
        seats=[tuple(map(int,m.split(","))) for m in re.findall(r"page=45 state=([\d,]+)",text)]
        assert (seats[-1][:len(spec["seats"])] if seats else tuple(range(len(spec["seats"]))))==spec["seats"],seats
    if spec.get("result")==1:
        # back in the character select the rows are the ones that were played
        again=[tuple(map(int,m.split(","))) for m in re.findall(r"page=48 state=([\d,]+)",text)]
        assert again[-1][:2]==(len(spec["rows"][0]),len(spec["rows"][1])),again
    if "assignments" in spec:
        actual=[tuple(map(int,m.split(","))) for m in re.findall(r"page=45 state=([\d,]+)",text)]
        assert actual==spec["assignments"],actual
    if spec.get("cpu"):
        # BT4's highest selectable difficulty is Z Hard, level 99.
        level=99 if marker and marker.exists() and json.loads(marker.read_text()).get('game')=='bt4' else 29
        assert f"page=46 state=1,{level},0,{spec['mode_id']},{level}" in text, "Chosen timer/per-fighter difficulty did not reach the loaded battle"
        assert not re.search(r"page=47 state=1,",text), "Hidden global CPU difficulty was edited"
        if marker and marker.exists() and json.loads(marker.read_text()).get('game')=='bt4':
            playlists=[list(map(int,line.split())) for line in re.findall(r"bt4 music list:([^\r\n]+)",text)]
            assert playlists and all(len(ids)==len(set(ids)) and ids.count(0)==1 and ids.count(24)==1 for ids in playlists),playlists
        controls=re.findall(r"tagteam control fighter=(\d+) control=(\d+) inject=(\d+)",text)
        assert controls and all(control=="2" and inject=="1" for _,control,inject in controls),controls
    if "rosters" in spec:
        rosters = [tuple(map(int, m.split(","))) for m in re.findall(r"page=45 state=([\d,]+)", text)]
        assert rosters == spec["rosters"], rosters
        for a, b, left, right, humans in rosters:
            players = [(packed >> (slot * 4)) & 15 for count, packed in ((a, left), (b, right)) for slot in range(count)]
            assert sorted(p for p in players if p) == list(range(1, humans + 1)), players
    if case == "settings":
        assert "tag_revive_seconds=4\n" in settings.read_text(), "Setting did not persist"
    if case == "revival-ring":
        assert "tag_revive_wave_height=9\n" in settings.read_text(), "Wave height did not persist"
        assert "tag_revive_wave_speed=125\n" in settings.read_text(), "Wave speed did not persist"
    if case=="setup-edit-cancel":
        changes=[tuple(map(int,m.split(","))) for m in re.findall(r"page=47 state=([-\d,]+)",text)]
        assert changes==[(0,1,4,2,0),(0,-1,3,2,0),(0,1,4,2,0)],changes
    if case == "camera-views":
        assert "tag_three_wide=0\n" in settings.read_text(), "Three-player layout did not persist"
    if case == "fusion-settings":
        assert "tag_fusion_swap_seconds=25\n" in settings.read_text(), "Fusion handoff interval did not persist"
    if case == "stage-settings":
        assert "tag_map_size=125\n" in settings.read_text(), "Expanded map size did not persist"
    if case == "control-bindings":
        assert "tag_target_button=2\n" in settings.read_text(), "Target button did not persist"
        assert "tag_menu_button=1\n" in settings.read_text(), "Mod menu button did not persist"
    if case == "settings-pagination":
        assert "tag_round_end_text=0\n" in settings.read_text(), "Last HUD text setting was not reachable"
    if case == "pause":
        assert {int(p) for p in re.findall(r"page=93 state=(\d+),", text)} == {2, 3}, "Controller scripts leaked between players"
        for pad in (2, 3):
            assert re.search(rf"page=90 state={pad},0,2,2,{pad}", text), f"P{pad+1} skill list did not open"
    if case in ("match", "free-for-all", "training", "unequal", "full-roster", "duplicates"):
        roster=spec.get("roster",(2,2)); actors=set(range(sum(roster)))
        assert {int(n) for n in re.findall(r"tagteam frame=150 fighter=(\d+)", text)} == actors
        assert {int(n) for n in re.findall(r"tagintro actor=(\d+)", text)} == actors
        assert {int(n) for n in re.findall(r"tagload batch=(\d+)", text)} == {1}
        actual_charas={int(a):int(c) for a,c in re.findall(r"tagteam frame=150 fighter=(\d+) chara=(\d+)",text)}
        intro_charas={int(a):int(c) for a,c in re.findall(r"tagintro actor=(\d+) chara=(\d+)",text)}
        assert intro_charas==actual_charas,(intro_charas,actual_charas)
        if case=="duplicates":
            assert len({actual_charas[i] for i in (0,2,4)})==1,actual_charas
        teams = {int(actor): int(team) for actor, team in re.findall(r"tagteam frame=150 fighter=(\d+) chara=\d+ team=(\d+)", text)}
        expected=[t for m in range(5) for t in range(2) if m<roster[t]]
        assert teams == ({i:i for i in actors} if case == "free-for-all" else dict(enumerate(expected))), teams
    return {"case": case, "passed": True, "log": str(path.relative_to(ROOT))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", default="port/build/bt3.exe")
    parser.add_argument("--renderer", choices=("none", "gpu"), default="gpu")
    parser.add_argument("--case", choices=tuple(CASES), action="append")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--lang", default="en", help="BT3_MENU_LANG of the run (en, es)")
    parser.add_argument("--shots", action="store_true", help="Take the pictures a case names (BT3_UI_SHOTS), into its folder")
    args = parser.parse_args()
    results = []
    for case in args.case or CASES:
        result = run(case, (ROOT / args.exe).resolve(), args.renderer,args.data,args.lang,args.shots)
        results.append(result)
        print(json.dumps(result), flush=True)
    (ROOT / "port/build/tag-menu-tests/results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
