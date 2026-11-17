# Native Tag Team Online

The Online Lobby connects **up to ten people**. Guests can join the host's
next match or watch it. Unclaimed fighters are CPUs, and everyone fights on
the field together. Teams can be different sizes.

From the normal game menu, press **Select**, then choose **Online Lobby**.
The online room uses native game menu pages, character artwork and stage previews.

You can also open **Play.cmd** for BT3 USA, or **Play.cmd**
for English BT4 B14 REV2. These launch the native game, not PCSX2. They use
separate online saves and settings; your offline saves are unchanged.

## Persistent Online Lobby

Choose **Select > Online Lobby** in the normal BT3 or BT4 main menu.
The Windows and Linux launchers both include this menu entry.

An Online Lobby holds the host and up to nine guests. The host uses the normal
**Modded Modes** main menu, including its game artwork and challenge submenus.
The host does not load or simulate the practice map, so its map audio does not
play behind the menu. Guests enter a practice map with no Ready/Fight sequence
or time limit. BT3 uses Kami's Lookout and BT4 uses South City, both at 200% size.
Six Saibamen stand in a row, labelled **Training Dummy** and the game's five
difficulty levels (including **Z Hard** in BT4).

- The training dummy does not fight back. The other dummies engage after you
  attack them. When either fighter is knocked out, they recover after three
  seconds and the dummy returns to its station.
- Approach another guest and press **Square** to challenge them. They accept
  with **Square** nearby. Players cannot hurt each other before accepting.
  After a knockout, both recover and become neutral again. Only these player
  challenges count toward the lobby's wins, losses and draws.
- **Start** opens your local practice menu without stopping the world.
  **Change Fighter** uses the original character, form, equipment and costume
  screens, then replaces your fighter in the current map. Finish a challenge
  before changing fighters. If another guest is using the selector, your
  request waits for them to finish.
- The host chooses Duel, Free For All, Training, Gauntlet or World Tournament.
  Everyone moves to the shared team setup. **Start** claims an available slot;
  press it again to ready up. Select an available CPU slot to move there, or
  use **L1/R1** to change teams. **Triangle** releases your slot so you can watch.
  Gauntlet has five player slots; other modes allow ten. Unclaimed fighters
  are CPUs, and unclaimed guests can follow fighters or use free camera.
- For Team Battle the host's menu first asks **How many teams?** With
  **2 Teams** the setup page is the one described above. With 3, 4 or 5 Teams
  the room starts with two CPU fighters per team and the host on team 1, and
  every slot shows **TEAM n** in its team's colour (the colours of the match).
  **L1/R1** on a fighter you may change (your own; the host: any CPU) moves it
  to the previous or next team; the page then lists the teams in order again
  and the cursor stays on that fighter. **+ Add CPU** gives the new fighter to
  the team with the fewest. A team keeps at least one and at most five
  fighters, ten in the room: a change against that is refused with a notice.
  The match is the offline Team Battle with those teams (the last team
  standing, or the best share of health at time over), and when it ends every
  computer says which team won.
- World Tournament supports four entered teams. The host can watch or skip
  CPU-only bracket matches. Gauntlet has preset, music and Heal per Wave choices.
- When the session ends, the host returns to mode selection and guests return
  to practice, keeping their connections. The host can also cancel setup with
  **Triangle**. A guest leaving a match hands their fighter to the CPU. Losing
  the host ends the room.
- Guests who took no fighter watch the match on confirmed inputs. They are not
  part of the players' input exchange: a watcher with a slow or frozen game
  does not hold the fighters.
- Connected players and their round-trip ping to the host appear in the corner
  of the host's mode menu and the guests' practice view. This roster does not
  appear during the selected match. The host can press **R3**, select a guest,
  then press **Square** to remove them; **Triangle** returns to choosing modes.
  Guests can
  join an ongoing practice map; if a match is already underway, they wait for
  its next room transition.

Gameplay settings come from the host for the duration of the room. Each guest
keeps their own HUD and other display preferences, and their saved offline
settings are not overwritten. All computers need the same build and disc data.
Separate-PC internet play still needs a human playtest.

Connections are direct to the host's address and TCP port. This feature does
not depend on a matchmaking or relay service. On a local network, use the
host's local IPv4 address. Across the internet, use an address reachable from
the other computers; the host may need to forward the chosen TCP port.

The local lobby checks cover ten members with delayed input, joining practice
in progress, replacing a disconnected guest after a fighter change, arriving
during a match, and returning to practice on the same connections. They also
cover a full tournament, five gauntlet players with two viewers, local picker
confirmation/cancellation, host loss, kicking a guest, and restoring offline
save data and BT4 equipment afterward. They also cover a frozen fighter and a
frozen watcher during a lobby match, a guest that never finishes loading, and
a guest who joins on the tournament team page. These used real native
processes on one computer; they are not a substitute for a multi-PC playtest.

## Hosting and joining

Everyone needs matching game data and the same release. Windows and Linux
x86-64 players can share a room. Choose **Host a Room**, confirm the TCP
port (7001 by default), and open the lobby. Guests choose **Join a Room** and
enter the host's reachable IPv4 address and port.

The host chooses a mode from the normal Modded Modes menu. At team setup,
guests press **Start** to claim a place and choose their characters through
the game's normal selector. Guests without a slot watch the match. Loading
waits for the players before starting the entrances.

Each computer uses **Player 1's local input bindings**. Use **F1 > Controls**
to choose your keyboard/controller and bindings.

## Spectating

Spectators join **before the match starts** and stay connected across rematches.
They cannot send fighter inputs, ready up, change the roster, accept a fusion,
or take over a CPU. A spectator leaving does not stop the players.

- **L2 / R2**, or **[ / ]**: previous/next participant's view, including CPUs.
- **Select**, or **F**: toggle free camera.
- In free camera: left stick moves, right stick looks, L1/R1 change height.
  The keyboard equivalents use the local game bindings.
- The spectator panel also has clickable controls and **Leave match**.

The original health/ki panels follow the viewed fighter and their target.
Following a fused partner follows the shared fighter. Camera movement is local
to the spectator and does not affect the players' simulation.

## Results and connection problems

After a session ends, the host returns to mode selection and guests return to
the practice map on the same connection. A missing guest becomes a CPU during
a match; losing the host ends the room.

- A guest whose game goes silent without closing (a frozen program; sleep or a
  dropped link look the same to the host) is removed by the host after about
  five seconds. In a match their fighter becomes a CPU from the same moment on
  every computer and everybody else keeps playing; in practice the others go on.
- A guest who has not finished loading 45 seconds after the host is ready is
  removed the same way, and the match or the practice map starts without them.
- Messages name the player and the cause, for example "Player 3 stopped
  responding. Their fighter is now a CPU." A removed guest whose game wakes up
  shortly afterwards is told why, and can join again for the next match.
- A game that waits for other players for more than a second (inputs, loading,
  the result) shows who it is waiting for. Hold **Start** for a second on that
  screen to leave the room.
- A guest whose game waits while the host has been silent for ten seconds, or
  that loses the connection to the host, closes the room on its side and says so.
- If the checks of two computers ever differ, the match stops as before, and
  each of the two writes `tagnet-report.txt` beside its settings file
  (`bt3_settings.txt` in the game folder, or the folder of the file named by
  `BT3_SETTINGS`). The message on screen names the file. It holds the blank,
  both check values, the build and data identity, and every fighter's compared
  values on both computers at the last blank they agreed on and at the first
  one on which they differ, with the differing values named. Send both files
  with a report. The other members of the room are told that the games went
  out of sync.
- The compared values include every fighter's team, the number of teams and
  the winning team, so two computers that disagreed about the teams would stop
  at the first comparison instead of playing different matches; the report
  then names the team. A room whose teams break the rule above is refused by
  the guests ("The room contains unsupported fighters, outfits or rules.").

The compatibility check compares build and game-content fingerprints, not
installation paths. The first BT4 check reads its extracted resources and can
take a few minutes on a slow drive. Progress is shown and you can cancel.
Later launches reuse content hashes when
the files have not changed. This check happens before opening a room.

## Rollback and current coverage

Every player runs the complete battle locally, including the CPUs. Only agreed
inputs enter the simulation. Rollback saves the game heap, low-address arena,
scratch memory, stack and game globals, including all Tag Team modules and BT4
animation bookkeeping. It restores the whole battle before replaying late inputs;
it does not merely correct the human fighters' positions.

The host chooses the input delay when a session starts, from the pings it
measured in the room: two to five vertical blanks, the same on every computer
(two on a local network; more when the longest way between two players, which
for two guests goes through the host, is long: each blank of delay is one
blank less to predict and to roll back). Players predict up to eight blanks beyond
the slowest confirmed input and wait there.
Spectators and lobby guests without a fighter run confirmed inputs without
prediction.

The computers keep their clocks together. Each one measures how far it runs
ahead of the inputs it holds from every other player, the host passes these
numbers around, and a computer that is ahead of the slowest one lets its
vertical blanks come a little later (at most 5 ms each) until they agree.
Without this the computer that started first, or one that kept running while
another hitched, did all the predicting and rolling back, or stood waiting at
the prediction limit. This moves real time only: it is outside the rollback
state and outside the compared values. `BT3_TAG_NET_BALANCE=0` turns it off.

Shared random state,
fighter state, revival progress, fusion ownership/timers and assist state are
checked during play. A detected mismatch stops the match rather than continuing
with different outcomes. Network queues, spectator controls and local rendering
preferences stay outside rollback.

Every session starts all three of the game's random generators from agreed
values, and what a computer draws for its own picture moves none of them.
(The third one, behind the effects and the flight of stage debris, used to
keep whatever value each computer had: a host coming from its menu and guests
coming from practice then threw the same rubble differently, and when a piece
fell into water the games went out of sync. This was found in the lobby's
default stage during a match of three teams; it did not depend on the teams.)

Local Windows tests have exercised actual socket connections with:

- Ten human input producers in BT3 and BT4, including a BT3 room with ten spectators.
- Two players plus CPUs, with the host and a spectator exchanging roles before
  the match and exchanging back before the rematch.
- Delayed inputs that force rollback; separate full-state rewind comparisons.
- BT3 and BT4 revivals, fusion/control handoff/defusion, beam assists,
  simultaneous beam clashes, and rush/ultimate cinematics overlapping a transformation.
- Two completed rounds with all ten spectators returning to the room.
- Remote pause-menu open/cancel and Return to room, including Player 10's
  rendered BT4 view and controls.
- A player loading 20 seconds later, and host/player/spectator disconnections.
- GPU-rendered matches with audio enabled, per-player health/ki panels, and
  spectator view changes/free camera.

Windows/Linux connections have also exercised revivals, timed fusion and
defusion, beam assists, simultaneous clashes, overlapping cinematics and repeated
lobby returns, including delayed inputs and a rendered guest view. These are
same-PC checks; separate PCs over the internet and long sessions need further
playtesting. The shared build fingerprint checks game source and compiler
compatibility rather than requiring identical Windows and Linux executables.
Disc-content checks remain separate. All players still need the same disc revision.

Lobby rooms of three, four and five teams have been played on loopback by
three members (real processes, delayed inputs that force rollbacks, the
45 second time rule, played to time over): the members on three teams, two
members on one team, two members on the team that stands on both roster rows,
a member moving its fighter to another team before readying, and a member
frozen in the middle of the fight, whose fighter became a CPU while the two
others finished. In each room every copy started from the same table of teams
and named the same winning team, and no check differed. A Linux-only room and
a room of a Windows host, a Linux guest and a Windows guest gave the same. A
copy made to put one fighter on another team stopped the room at the first
comparison, with the report naming the team; a room sent with an empty team
was refused by both guests; and a program of the previous release was refused
by the host with "Online versions differ. Both players must install the same
update." The host's teams page and the room page were looked at in English and
Spanish (a rendered host driven by a scripted pad: choosing 3 Teams, moving a
CPU with R1, a refused change, Add CPU). These are same-PC runs with test
inputs: nobody has played such a room over the internet yet, and the winning
team's notice was read in the logs, not on a screen.

Online matches follow the host's game speed. Guests keep their own offline speed
preference when they leave the room.

The repeatable runner is `port/tests/tag_online_runtime.py`. Its default tests
use isolated saves/settings and real game processes on loopback. For example:

```text
python port/tests/tag_online_runtime.py --spectators 10 --input --lag
python port/tests/tag_online_runtime.py --players 10 --spectators 10 --input --lag
python port/tests/tag_online_runtime.py --bt4 --players 2 --spectators 1 --swap-roles --case 5 --rounds 2 --frames 5000
python port/tests/tag_online_runtime.py --bt4 --case 2 --spectators 1 --input --lag --frames 1850
python port/tests/tag_online_runtime.py --case 5 --spectators 10 --rounds 2 --frames 5000
python port/tests/tag_online_runtime.py --party --rounds 1 --players 3 --party-mode 0 --input --lag --freeze player2 --frames 1800
python port/tests/tag_online_runtime.py --party --rounds 1 --players 3 --party-mode 0 --join-in-setup --no-fighter guest --freeze guest --frames 1800
python port/tests/tag_online_runtime.py --party --rounds 1 --players 3 --party-mode 0 --load-delay 130000 --load-delay-round 2 --frames 1800
```

`--freeze NAME` suspends that client's process once every client has passed
`--freeze-at` in a match, and the run passes when the others confirm `--frames`
more blanks. `--no-fighter NAME` keeps a lobby member without a fighter, and
`--join-in-setup` connects the third member on the team setup page.

Every client's periodic log line (`tagnet: frame N, ...`, every 600 blanks)
ends with what happened since the previous one: real time, rollbacks with
their mean and greatest depth and what re-running them cost, waits at the
prediction limit and the time spent in them, the mean lead over the slowest
confirmed input, and how far the clock balance stretched the blanks. The
runner sums them per client (`STATS`). For comparisons:

```text
python port/tests/tag_online_runtime.py --players 10 --input --paced --frames 3600 --net-balance 0
python port/tests/tag_online_runtime.py --players 10 --input --paced --frames 3600 --slow guest:16
python port/tests/tag_online_runtime.py --players 4 --input --paced --frames 3600 --proxy <delay_proxy.py> --proxy-delay 40
python port/tests/tag_online_runtime.py --players 2 --input --frames 3000 --differ guest:2710:1
```

`--paced` runs every client at display speed. `--slow NAME:MS` makes every
blank of one client longer and `--hitch NAME:BLANK:MS` stops it once.
`--proxy SCRIPT --proxy-delay MS [--proxy-stall MS:SECONDS]` puts a loopback
delay proxy between the guests and the host. `--net-balance 0`, `--net-input-delay N` and
`--net-window N` (8 to 12; 8 is what players get) switch the smoothness
changes for a comparison. `--differ NAME:BLANK[:FIGHTER]`
changes one fighter's health on one copy: the room must stop and both sides
must write the report. These are same-PC runs through a delay proxy: a
stand-in for a line with delay, not a measurement of the internet.

Rooms of three to five teams:

```text
python port/tests/tag_online_runtime.py --party --rounds 1 --party-mode 0 --players 3 --teams 3 --team guest:2 --team player2:3 --match-time 5 --input --lag
python port/tests/tag_online_runtime.py --party --rounds 1 --party-mode 0 --players 3 --teams 5 --team guest:5 --team player2:5 --match-time 5 --input --lag
python port/tests/tag_online_runtime.py --party --rounds 1 --party-mode 0 --players 3 --teams 4 --move guest:3 --match-time 5 --input --lag
python port/tests/tag_online_runtime.py --party --rounds 1 --party-mode 0 --players 3 --teams 3 --team-differ guest:1 --match-time 5
```

`--teams N` lets the host choose Team Battle with N teams. `--team NAME:T`
makes a member take a free fighter of team T, and `--move NAME:T` makes it move
its own fighter there with the edit L1/R1 send, before it readies.
`--match-time` sets the time rule (5 is 45 seconds). The runner then requires
the same table of teams and the same winning team in every client's log.
`--bad-teams` has the host send a room with an empty team, which every guest
must refuse. `--team-differ NAME:SLOT` puts one fighter on another team on one
copy only: the room must stop with a report that names the team.
`--until-decided` (with `--freeze`) lets the others play the match to its
result. `--host-pad SCRIPT` drives a rendered host through its own menu and
`--shots NAME:FRAME,...` saves that client's picture at those frames.

Run one test at a time, or give parallel tests different `--port` values. The
runner closes only the processes it starts. Logs go under `port/build/tag-online/`.

`python port/tests/tag_online_room.py` checks a real host's character edits,
ready resets, player-slot ownership, spectator permissions and capacity,
role changes, build mismatch rejection, and replacement players joining an existing room.
