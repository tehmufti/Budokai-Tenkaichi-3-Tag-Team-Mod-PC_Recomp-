#!/usr/bin/env python3
"""Team Battle with three to five teams: headless CPU matches through the real loader.

The demo launcher is fed by BT3_TAG_TEAMS (the session lays the teams out on the two native rows, as the menus
do). For every case this checks, from the program's own trace:
  - every fighter is on the team the layout rules give its roster slot;
  - every fighter only ever targets a fighter of another team;
  - the match is decided once; a knock-out leaves exactly one team with a living fighter and names it; a time over
    names the team with the largest share of its full health, computed here from the logged sums (equal shares:
    the lower team number); the fighter that represents the winner belongs to it.
--synctest runs the match under the rewind harness (every blank twice) and requires that no blank ends differently.
--fixture runs the in-game checks of three teams of two with one player (BT3_TAG_TEST_SQUAD): which features a
match of three teams offers, the session calls behind the team setup (sizes, seats, the team that stands on both
rows, the online room's table), and a fallen player's view going to the living teammate and taking it over.

    python port/tests/tag_squad_runtime.py --exe port/build/bt3.exe --data gamedata [--teams 2,2,2 ...]
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
SUMS = re.compile(r"tagdecided team=(\d+) health=(-?\d+) full=(\d+) living=(\d+)")
DECIDED = re.compile(r"tagdecided reason=(\w+) winner_team=(-?\d+) actor=(-?\d+) teams=(\d+)")
SYNC = re.compile(r"sync: (\d+) blanks each run twice, rewinding (\d+) at a time; (\d+) ended differently")
DEFAULT = ["1,1,1", "2,2,2", "3,3,3", "5,3,2", "4,4,1,1", "2,2,2,2,2"]


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


def actor_teams(size):
    """Runtime fighters are interleaved: member 0 of row 0, member 0 of row 1, member 1 of row 0, ..."""
    rows = layout(size)
    return [rows[r][m] for m in range(5) for r in range(2) if m < len(rows[r])], rows


def run_case(exe, data, output, teams, limit, stage, synctest, timeout, expect=None, health=None, sync_start=1):
    size = [int(n) for n in teams.split(",")]
    name = "-".join(map(str, size)) + ("" if limit is None else f"-time{limit}") + ("" if not synctest else "-sync" if sync_start == 1 else f"-sync{sync_start}") + \
        ("" if stage is None else f"-stage{stage}") + ("" if health is None else f"-hp{health}")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BT3_")}
    env.update(BT3_GS="none", BT3_DEMO="1", BT3_SETTINGS="", BT3_SAVES=str(output / "saves" / name),
               BT3_NOSOUND="1", SDL_AUDIO_DRIVER="dummy", BT3_UPDATE_CHECK="0",
               BT3_TAG_TEAM="1", BT3_TAG_TRACE="1", BT3_TAG_TEAMS=teams)
    if data:
        env["BT3_DATA"] = str(Path(data).resolve())
    if limit is not None:
        env["BT3_TAG_TEAMS_TIME"] = str(limit)
    if stage is not None:
        env["BT3_TEST_STAGE"] = str(stage)
    if health is not None:
        env["BT3_TAG_TEAMS_HEALTH"] = str(health)
    if synctest:
        env.update(BT3_SYNCTEST=str(sync_start), BT3_SYNCTEST_DEPTH=str(synctest))
    log = output / (name + ".log")
    start = time.monotonic()
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run([str(exe)], cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    text = log.read_text(encoding="utf-8", errors="replace")
    assert result.returncode == 0, f"{name}: exit {result.returncode}; see {log}"
    assert "bt3: battle finished" in text, f"{name}: no completed battle; see {log}"
    assert "bt3: sound:" not in text, f"{name}: a sound device was opened"
    expected, rows = actor_teams(size)
    trace = [tuple(map(int, row)) for row in TRACE.findall(text)]
    actors = sorted({row[1] for row in trace})
    assert actors == list(range(sum(size))), f"{name}: fighters in the trace: {actors}"
    for frame, actor, chara, team, target, hp, action in trace:
        assert team == expected[actor], f"{name}: fighter {actor} is on team {team}, the layout says {expected[actor]}"
        assert 0 <= target < len(expected) and expected[target] != team, \
            f"{name}: frame {frame}: fighter {actor} (team {team}) targets fighter {target} (team {expected[target]})"
    assert len({(row[1], row[5]) for row in trace}) > len(actors), f"{name}: nobody's health ever changed"
    decided = DECIDED.findall(text)
    if synctest:  # (every blank runs twice there: the same decision is printed by both passes)
        decided = list(dict.fromkeys(decided))
    assert len(decided) == 1, f"{name}: decided {len(decided)} times; see {log}"
    reason, winner, actor, count = decided[0][0], int(decided[0][1]), int(decided[0][2]), int(decided[0][3])
    sums = {int(t): (int(h), int(f), int(l)) for t, h, f, l in SUMS.findall(text)}
    assert count == len(size) and sorted(sums) == list(range(len(size))), f"{name}: team sums {sums}"
    living = [t for t in sums if sums[t][2] > 0]
    if reason == "ko":
        assert len(living) <= 1, f"{name}: knock-out with living teams {living}"
        want = living[0] if living else -1
    else:
        want = -1
        for t in living:  # ascending: an equal share keeps the lower team number
            if want < 0 or sums[t][0] * sums[want][1] > sums[want][0] * sums[t][1]:
                want = t
    assert winner == want, f"{name}: the program names team {winner}, the sums say {want}: {sums}"
    assert (winner < 0 and actor < 0) or expected[actor] == winner, f"{name}: fighter {actor} does not represent team {winner}"
    assert expect is None or reason == expect, f"{name}: decided by {reason}, expected {expect}; see {log}"
    report = {"case": name, "rows": [" ".join(str(t + 1) for t in r) for r in rows], "reason": reason,
              "winner_team": winner + 1 if winner >= 0 else 0, "representative": actor, "last_frame": trace[-1][0],
              "sums": {str(t + 1): {"health": sums[t][0], "full": sums[t][1], "living": sums[t][2]} for t in sums},
              "seconds": round(time.monotonic() - start, 2), "log": str(log)}
    if synctest:
        runs = [tuple(map(int, row)) for row in SYNC.findall(text)]
        assert runs and all(row[2] == 0 for row in runs) and "it ends differently" not in text, \
            f"{name}: the rewind harness saw a difference; see {log}"
        report["sync_blanks"] = runs[-1][0]
    return report


def run_fixture(exe, data, output, timeout):
    env = {k: v for k, v in os.environ.items() if not k.startswith("BT3_")}
    env.update(BT3_GS="none", BT3_DEMO="1", BT3_SETTINGS="", BT3_SAVES=str(output / "saves" / "fixture"),
               BT3_NOSOUND="1", SDL_AUDIO_DRIVER="dummy", BT3_UPDATE_CHECK="0", BT3_TAG_TEAM="1", BT3_TAG_TRACE="1",
               BT3_TAG_TEAMS="2,2,2", BT3_TAG_PLAY="1", BT3_TAG_TEST_SQUAD="1")
    if data:
        env["BT3_DATA"] = str(Path(data).resolve())
    log = output / "fixture.log"
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run([str(exe)], cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    text = log.read_text(encoding="utf-8", errors="replace")
    assert result.returncode == 0 and "PASS check=99" in text and "FAIL" not in text, f"fixture failed; see {log}"
    # (729 is only printed when the takeover never became possible)
    assert all(f"PASS check={n}" in text for n in range(720, 746) if n != 729), f"incomplete fixture; see {log}"
    print("PASS fixture: three teams, session sizes, seats, split team and room table, revive, takeover, fusion, "
          "beam assists and Outnumbered offered, fallen player's view on the teammate, takeover", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exe", default="port/build/bt3.exe" if os.name == "nt" else "port/build/bt3_64")
    parser.add_argument("--data", help="Game data folder (BT3_DATA); default: gamedata in the tree")
    parser.add_argument("--teams", action="append", help="Fighters per team, for example 2,2,2 (repeatable)")
    parser.add_argument("--time", type=int, help="Time-limit setting: 0 none (the default here), 1..4 = 60/90/180/240 s, 5 the demo's own")
    parser.add_argument("--stage", type=int)
    parser.add_argument("--health", type=int, help="Percentage of its health every fighter starts with (shorter knock-out matches)")
    parser.add_argument("--synctest", type=int, nargs="?", const=1, help="Rewind harness; the value is the depth in blanks")
    parser.add_argument("--expect", choices=("ko", "time"), help="How the match must be decided")
    parser.add_argument("--synctest-start", type=int, default=1, help="First blank the rewind harness runs at")
    parser.add_argument("--fixture", action="store_true", help="Only the in-game checks (BT3_TAG_TEST_SQUAD)")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", help="Folder for logs; default port/build/tag-squad-tests")
    args = parser.parse_args()
    exe = Path(args.exe)
    if not exe.is_absolute():
        exe = ROOT / exe
    output = Path(args.output) if args.output else ROOT / "port/build/tag-squad-tests" / ("windows" if exe.suffix.lower() == ".exe" else "linux")
    output.mkdir(parents=True, exist_ok=True)
    if args.fixture:
        run_fixture(exe, args.data, output, args.timeout)
        return
    limit = 0 if args.time is None else args.time
    reports = []
    for teams in args.teams or DEFAULT:
        report = run_case(exe, args.data, output, teams, limit, args.stage, args.synctest, args.timeout, args.expect, args.health,
                          args.synctest_start)
        reports.append(report)
        extra = f", {report['sync_blanks']} blanks rewound without a difference" if args.synctest else ""
        print(f"PASS {teams}: rows {' / '.join(report['rows'])}; {report['reason']}, team {report['winner_team']} wins "
              f"(fighter {report['representative']}) at step {report['last_frame']}+; sums {json.dumps(report['sums'])}"
              f"{extra} ({report['seconds']}s)", flush=True)
    (output / "results.json").write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
