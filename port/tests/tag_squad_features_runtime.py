#!/usr/bin/env python3
"""Team features in a Team Battle of three or more teams: headless, through the real loader.

Every feature runs twice: with its fighters on one roster row ("same") and with the team that stands on both
rows ("split": team 3 of 3-3-3 is fighters 6 and 8 on row 0 and fighter 7 on row 1). The matches are fed by
BT3_TAG_TEAMS; the in-game cases are BT3_TAG_TEST_SQUAD=2..6 (src/battle/tag_team_test.c), which direct single
fighters while everybody else stands still.

  hits         CPU matches with BT3_TAG_HIT_TRACE: no hit between teammates, every pair of teams exchanges hits,
               also two enemy teams on one roster row
  revive       a fighter of another team beside the body does nothing; the teammate revives
  takeover     the fallen player's view goes to the teammate, the takeover, and nobody is offered once the team
               is down
  fusion-dance the pair fuses (an enemy with the partner's character is not taken), the timed separation with one
               broken request (BT3_TAG_TEST_DEFUSE_BREAK=2), no partner on another team afterwards
  fusion-players the same with two players as the pair on the split team: asked with R3, one view while fused
  fusion-potara the pair stays fused; the time over rule's logged sums against the fixture's own
  assist       the teammate helps a beam struggle, a third team's fighter cannot; its beam hits the helper during
               the struggle and the struggling fighter after it
  outnumbered  the help follows the largest enemy team: the logged numbers against the rule written again here

    python port/tests/tag_squad_features_runtime.py --exe port/build/bt3.exe --data gamedata [--case revive-split ...]
"""
import argparse
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
TRACE = re.compile(r"tagteam frame=(\d+) fighter=(\d+) chara=(\d+) team=(\d+) target=(\d+) hp=(-?\d+) action=(\d+)")
HIT = re.compile(r"taghit victim=(-?\d+) source=(-?\d+) lost=(-?\d+) teams=(-?\d+),(-?\d+)")
NOTE = re.compile(r"tagteam fixture note id=(\d+) values=(-?\d+),(-?\d+),(-?\d+),(-?\d+)")
CHECK = re.compile(r"tagteam fixture: (PASS|FAIL) check=(\d+)")
SUMS = re.compile(r"tagdecided team=(\d+) health=(-?\d+) full=(\d+) living=(\d+)")
DECIDED = re.compile(r"tagdecided reason=(\w+) winner_team=(-?\d+) actor=(-?\d+) teams=(\d+)")
BALANCE = re.compile(r"tagbalance actor=(\d+) team=(\d+) own=(\d+) enemy=(\d+) dealt=(\d+) taken=(\d+)")
FUSION = re.compile(r"tagfusion tick=(\d+) actor=(\d+) event=(\d+)")
REVIVED = re.compile(r"tagteam: revived actor=(\d+) helper=(\d+) hp=(\d+)")


def layout(size):
    """The rules of include/battle/tag_squad.h, written again on their own: rows of team numbers."""
    teams, total = len(size), sum(size)
    best = None
    for n in range(1, teams + 1):
        for row0 in itertools.combinations(range(teams), n):
            if row0[0] != 0:
                continue
            a = sum(size[t] for t in row0)
            if a > 5 or not 1 <= total - a <= 5:
                continue
            key = (abs(2 * a - total), list(row0))
            if best is None or key < best:
                best = key
    split, head = None, 0
    if best is None:
        for s in range(teams - 1, 0, -1):
            for n in range(1, teams):
                for row0 in itertools.combinations([t for t in range(teams) if t != s], n):
                    if row0[0] != 0:
                        continue
                    k = 5 - sum(size[t] for t in row0)
                    if not 1 <= k <= size[s] - 1:
                        continue
                    if best is None or list(row0) < best[1]:
                        best, head = (0, list(row0)), k
            if best is not None:
                split = s
                break
    assert best is not None, size
    rows = [[], []]
    for t in range(teams):
        if t != split:
            rows[0 if t in best[1] else 1] += [t] * size[t]
    if split is not None:
        rows[0] += [split] * head
        rows[1] += [split] * (size[split] - head)
    return rows


def fighters(size):
    """Team and roster row of every fighter (member 0 of row 0, member 0 of row 1, member 1 of row 0, ...)."""
    rows = layout(size)
    order = [(r, m) for m in range(5) for r in range(2) if m < len(rows[r])]
    return [rows[r][m] for r, m in order], [r for r, m in order]


MORE = {}  # --env: switches for one run (traces)

# name: (teams, squad case, actors, extra environment, checks that must have passed)
SAME, SPLIT = "2,2,2", "3,3,3"
CASES = {
    "hits-same": (SAME, 0, "", {"BT3_TAG_TEAMS_TIME": "1"}, ()),
    "hits-split": (SPLIT, 0, "", {"BT3_TAG_TEAMS_TIME": "1"}, ()),
    # rescuer, body, outsider (on the body's row)
    "revive-same": (SAME, 2, "1,3,4", {}, range(750, 759)),
    "revive-split": (SPLIT, 2, "6,7,1", {}, range(750, 759)),
    # the player's fighter, the teammate taken over, a teammate that falls first
    "takeover-same": (SAME, 3, "0,2,-1", {"BT3_TAG_PLAY": "1"}, (750, *range(761, 767), *range(768, 773))),
    "takeover-split": (SPLIT, 3, "8,7,6", {"BT3_TAG_PLAY": "1", "BT3_TAG_TEST_SEATS": "8"},
                       (750, *range(761, 767), *range(768, 773))),
    # the pair, an enemy with the partner's character
    "fusion-dance-same": (SAME, 4, "0,2,1", {"BT3_TAG_TEST_CAST": "0:3,2:34,1:34", "BT3_TAG_FUSION_RESULT": "53",
                                             "BT3_TAG_TEST_DEFUSE_BREAK": "2"}, (750, *range(780, 788), *range(789, 795))),
    "fusion-dance-split": (SPLIT, 4, "6,7,1", {"BT3_TAG_TEST_CAST": "6:3,7:34,1:34", "BT3_TAG_FUSION_RESULT": "53",
                                               "BT3_TAG_TEST_DEFUSE_BREAK": "2"}, (750, *range(780, 788), *range(789, 795))),
    # the pair are players 1 and 2: asked with R3, one view while fused, two again afterwards
    "fusion-players-split": (SPLIT, 4, "6,7,1", {"BT3_TAG_TEST_CAST": "6:3,7:34,1:34", "BT3_TAG_FUSION_RESULT": "53",
                                                 "BT3_TAG_PLAY": "2", "BT3_TAG_TEST_SEATS": "6,7"},
                             (750, *range(780, 788), *range(789, 795), 796, 797, 798)),
    "fusion-potara-same": (SAME, 4, "0,2,1", {"BT3_TAG_TEST_CAST": "0:3,2:34,1:34", "BT3_TAG_FUSION_RESULT": "51"},
                           (750, *range(780, 789), 795)),
    "fusion-potara-split": (SPLIT, 4, "6,7,1", {"BT3_TAG_TEST_CAST": "6:3,7:34,1:34", "BT3_TAG_FUSION_RESULT": "51"},
                            (750, *range(780, 789), 795)),
    # the fighter in the struggle, its helper, the enemy in the struggle, a third team's fighter
    "assist-same": (SAME, 5, "3,1,4,0", {"BT3_TAG_TEST_CAST": "3:10,1:10,4:10,0:10"}, (750, *range(800, 812), 813)),
    "assist-split": (SPLIT, 5, "7,6,1,0", {"BT3_TAG_TEST_CAST": "7:10,6:10,1:10,0:10"}, (750, *range(800, 812), 813)),
    # who falls at the first step (two fighters), who at the second
    "outnumbered-same": ("1,2,3", 6, "1,-1,3,-1", {"BT3_TAG_BALANCE_TRACE": "1"}, (820,)),
    "outnumbered-split": (SPLIT, 6, "0,1,6,8", {"BT3_TAG_BALANCE_TRACE": "1"}, (820,)),
}


def is_bt4(data):
    marker = Path(data) / "native-disc.json" if data else None
    try:
        return bool(marker) and json.loads(marker.read_text(encoding="utf-8")).get("game") == "bt4"
    except (OSError, ValueError):
        return False


def run(exe, data, output, name, timeout):
    teams, case, actors, extra, wanted = CASES[name]
    if case == 4 and is_bt4(data):
        # BT4's Vegeta is 31 (34 is another character there) and its recipes for both fused fighters are
        # Vegeta's: he starts, Goku (3) is the partner.
        a, b, e = actors.split(",")
        extra = dict(extra, BT3_TAG_TEST_CAST=f"{a}:31,{b}:3,{e}:3")
    size = [int(n) for n in teams.split(",")]
    env = {k: v for k, v in os.environ.items() if not k.startswith("BT3_")}
    env.update(BT3_GS="none", BT3_DEMO="1", BT3_SETTINGS="", BT3_SAVES=str(output / "saves" / name),
               BT3_NOSOUND="1", SDL_AUDIO_DRIVER="dummy", BT3_UPDATE_CHECK="0", BT3_TAG_TEAM="1", BT3_TAG_TRACE="1",
               BT3_TAG_HIT_TRACE="1", BT3_TAG_TEAMS=teams, BT3_TAG_TEAMS_TIME="0")
    if case:
        env.update(BT3_TAG_TEST_SQUAD=str(case), BT3_TAG_TEST_SQUAD_ACTORS=actors)
    env.update(extra)
    env.update(MORE)
    if data:
        env["BT3_DATA"] = str(Path(data).resolve())
    log = output / (name + ".log")
    start = time.monotonic()
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run([str(exe)], cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    text = log.read_text(encoding="utf-8", errors="replace")
    assert "bt3: sound:" not in text, f"{name}: a sound device was opened"
    checks = CHECK.findall(text)
    failed = [n for state, n in checks if state == "FAIL"]
    assert result.returncode == 0 and not failed, f"{name}: exit {result.returncode}, failed checks {failed}; see {log}"
    team, row = fighters(size)
    notes = {}
    for n, *values in NOTE.findall(text):
        notes.setdefault(int(n), []).append(tuple(map(int, values)))
    report = {"case": name, "teams": teams, "rows": [" ".join(str(t + 1) for t in r) for r in layout(size)],
              "seconds": round(time.monotonic() - start, 1), "log": str(log)}
    if case:
        passed = {int(n) for state, n in checks if state == "PASS"}
        missing = [n for n in (*wanted, 99) if n not in passed]
        assert not missing, f"{name}: checks never reached: {missing}; see {log}"
        report["checks"] = len(passed)
    if case in (2, 3, 4, 5):
        who = [int(n) for n in actors.split(",")]
        ra, rb, re_, t = notes[750][0]
        assert (ra, rb) == (row[who[0]], row[who[1]]) and t == team[who[0]] == team[who[1]], f"{name}: rows {notes[750]}"
        assert (ra != rb) == name.endswith("-split"), f"{name}: fighters {who[0]} and {who[1]} stand on rows {ra} and {rb}"
        report["fighters"] = {"a": who[0], "b": who[1], "rows": [ra, rb], "team": t + 1, "others": who[2:]}
    globals()["check_" + name.rsplit("-", 1)[0].replace("-", "_")](name, text, size, team, row, notes, report, actors)
    return report


def check_hits(name, text, size, team, row, notes, report, actors):
    assert "bt3: battle finished" in text, f"{name}: no completed battle"
    for frame, actor, chara, t, target, hp, action in (tuple(map(int, r)) for r in TRACE.findall(text)):
        assert t == team[actor] and team[target] != t, f"{name}: frame {frame}: fighter {actor} (team {t}) targets {target}"
    pairs, same_row, friendly, unowned, cross = {}, 0, [], 0, 0
    hits = [tuple(map(int, h)) for h in HIT.findall(text)]
    for victim, source, lost, vt, st in hits:
        if not 0 <= source < len(team):
            unowned += 1
            continue
        assert vt == team[victim] and st == team[source], f"{name}: teams in the hit line {victim, source, vt, st}"
        if vt == st:
            friendly.append((source, victim, lost))
            continue
        pairs[(st, vt)] = pairs.get((st, vt), 0) + 1
        same_row += row[victim] == row[source]
        cross += row[victim] != row[source]
    assert not friendly, f"{name}: hits between teammates (source, victim, lost): {friendly[:10]}"
    teams = range(len(size))
    silent = [(a + 1, b + 1) for a in teams for b in teams if a < b and not pairs.get((a, b)) and not pairs.get((b, a))]
    assert not silent, f"{name}: no hit between teams {silent}: {pairs}"
    assert same_row and cross, f"{name}: hits on one row {same_row}, across rows {cross}"
    report.update(hits=len(hits), unowned=unowned, same_row_enemy_hits=same_row, cross_row_hits=cross,
                  by_teams={f"{a + 1}>{b + 1}": n for (a, b), n in sorted(pairs.items())})
    split = [t for t in teams if len({row[f] for f in range(len(team)) if team[f] == t}) > 1]
    if split:
        members = [f for f in range(len(team)) if team[f] == split[0]]
        given = {f: sum(1 for v, s, *_ in hits if s == f) for f in members}
        taken = {f: sum(1 for v, s, *_ in hits if v == f) for f in members}
        assert all(given.values()) and all(taken.values()), f"{name}: split team hits given {given}, taken {taken}"
        report["split_team"] = {"team": split[0] + 1, "fighters": members, "given": given, "taken": taken}


def check_revive(name, text, size, team, row, notes, report, actors):
    a, b, e = (int(n) for n in actors.split(","))
    revived = [tuple(map(int, r)) for r in REVIVED.findall(text)]
    assert revived == [(b, a, revived[0][2])], f"{name}: revivals {revived}"
    assert team[e] != team[b] and row[e] == row[b], f"{name}: the outsider is fighter {e}"
    ticks, duration, before, after = notes[757][0]
    report.update(revived_by=a, outsider=e, outsider_row=row[e], ticks=ticks, health=revived[0][2], stocks_paid=before - after)


def check_takeover(name, text, size, team, row, notes, report, actors):
    report["note"] = "view on the teammate, takeover, nobody offered once the team is down"


def check_fusion_dance(name, text, size, team, row, notes, report, actors):
    a = int(actors.split(",")[0])
    events = [int(e) for t, f, e in FUSION.findall(text) if int(f) == a]
    assert 2 in events and events.count(1) >= 2 and 4 in events, f"{name}: separation events {sorted(set(events))}"
    assert events.index(2) < len(events) - 1 - events[::-1].index(4), f"{name}: the broken request came after the separation"
    report.update(fused_ticks=notes[789][0][0], requests=events.count(1), lost=events.count(2), forced=events.count(3))


def check_fusion_players(name, text, size, team, row, notes, report, actors):
    a = int(actors.split(",")[0])
    events = [int(e) for t, f, e in FUSION.findall(text) if int(f) == a]
    assert 1 in events and 4 in events, f"{name}: separation events {sorted(set(events))}"
    report.update(fused_ticks=notes[789][0][0], players=2)


def check_fusion_potara(name, text, size, team, row, notes, report, actors):
    sums = {int(t): (int(h), int(f), int(l)) for t, h, f, l in SUMS.findall(text)}
    decided = DECIDED.findall(text)
    assert len(decided) == 1 and decided[0][0] == "time", f"{name}: decisions {decided}"
    want = {t: notes[790 + t][0][:3] for t in range(len(size))}
    assert sums == want, f"{name}: logged sums {sums}, the fixture's own {want}"
    best = -1
    for t in sorted(sums):
        if sums[t][2] and (best < 0 or sums[t][0] * sums[best][1] > sums[best][0] * sums[t][1]):
            best = t
    assert int(decided[0][1]) == best, f"{name}: winner {decided[0][1]}, the sums say {best}"
    report.update(sums={str(t + 1): {"health": s[0], "full": s[1], "living": s[2]} for t, s in sums.items()}, winner_team=best + 1)


def check_assist(name, text, size, team, row, notes, report, actors):
    a, b, c, d = (int(n) for n in actors.split(","))
    active, assisted, fired, during = notes[809][0]
    on_helper, on_fighter, after, lost = notes[810][0]
    assert len({team[a], team[c], team[d]}) == 3, f"{name}: teams of {a, c, d}"
    assert after > 0 and lost > 0, f"{name}: the shot after the struggle: {notes[810]}"
    report.update(struggle_ticks=active, third_team_fighter=d,
                  during_struggle={"hits_on_helper": on_helper, "hits_on_struggler": on_fighter,
                                   "flagAA_frozen_of_struggler_and_helper": notes.get(813, [None])[0],
                                   "helper_hits_struggler_hits_helping_multiplier_90_ticks_later": notes.get(814, [None])[0]},
                  after_struggle={"hits_on_struggler": after, "health_lost": lost})


def check_outnumbered(name, text, size, team, row, notes, report, actors):
    falls = [int(n) for n in actors.split(",")]
    latest, steps, step = {}, {}, None
    for line in text.splitlines():
        m = BALANCE.search(line)
        if m:
            latest[int(m.group(1))] = tuple(map(int, m.groups()[1:]))
        m = NOTE.search(line)
        if m and int(m.group(1)) == 830:
            step = int(m.group(2))
            steps[step] = {"numbers": dict(latest), "damage": []}
        elif m and int(m.group(1)) == 831:
            steps[step]["damage"].append(tuple(map(int, m.groups()[1:4])))
    assert sorted(steps) == [0, 1, 2], f"{name}: steps {sorted(steps)}"
    table = []
    for step in range(3):
        down = {f for f in falls[:2 * step] if f >= 0}
        alive = [f for f in range(len(team)) if f not in down]
        count = {t: sum(1 for f in alive if team[f] == t) for t in range(len(size))}
        want = {}
        for f in alive:
            own, enemy = count[team[f]], max(n for t, n in count.items() if t != team[f])
            everybody = sum(n for t, n in count.items() if t != team[f])
            small = own < enemy
            want[f] = (team[f], own, enemy, min(300, 100 + 15 * (enemy - own) // own) if small else 100,
                       max(40, 100 - 10 * (enemy - own) // own) if small else 100)
            table.append({"step": step, "fighter": f, "team": team[f] + 1, "row": row[f], "own": own, "largest_enemy_team": enemy,
                          "all_enemies": everybody, "dealt": want[f][3], "taken": want[f][4]})
        got = {f: steps[step]["numbers"].get(f) for f in alive}
        assert got == want, f"{name}: step {step}: logged {got}, the rule says {want}"
        assert len(steps[step]["damage"]) == len(alive), f"{name}: step {step}: damage notes {steps[step]['damage']}"
        for source, victim, value in steps[step]["damage"]:
            assert value == 1000 * want[source][3] // 100 * want[victim][4] // 100, \
                f"{name}: step {step}: 1000 points of fighter {source} on {victim} became {value}"
    assert any(r["dealt"] > 100 and r["largest_enemy_team"] != r["all_enemies"] for r in table), f"{name}: nothing told the rules apart"
    report["numbers"] = table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exe", default="port/build/bt3.exe" if os.name == "nt" else "port/build/bt3_64")
    parser.add_argument("--data", help="Game data folder (BT3_DATA); default: gamedata in the tree")
    parser.add_argument("--case", action="append", choices=sorted(CASES), help="Only these cases (repeatable)")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--env", action="append", default=[], metavar="NAME=VALUE", help="One more switch for the game (repeatable)")
    parser.add_argument("--output", help="Folder for logs; default port/build/tag-squad-features")
    args = parser.parse_args()
    exe = Path(args.exe)
    if not exe.is_absolute():
        exe = ROOT / exe
    output = Path(args.output) if args.output else ROOT / "port/build/tag-squad-features" / ("windows" if exe.suffix.lower() == ".exe" else "linux")
    output.mkdir(parents=True, exist_ok=True)
    MORE.update(item.split("=", 1) for item in args.env)
    reports, bad = [], 0
    for name in args.case or list(CASES):
        try:
            report = run(exe, args.data, output, name, args.timeout)
        except (AssertionError, subprocess.TimeoutExpired, KeyError, IndexError) as error:
            bad += 1
            reports.append({"case": name, "failed": str(error)})
            print(f"FAIL {name}: {error}", flush=True)
            continue
        reports.append(report)
        brief = {k: v for k, v in report.items() if k not in ("case", "log", "numbers", "teams")}
        print(f"PASS {name} ({report['teams']}): {json.dumps(brief)}", flush=True)
    (output / "results.json").write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
