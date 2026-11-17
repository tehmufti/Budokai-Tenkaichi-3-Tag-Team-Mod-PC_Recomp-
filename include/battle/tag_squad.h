#ifndef BATTLE_TAG_SQUAD_H
#define BATTLE_TAG_SQUAD_H
/* Team Battle with three to five teams: where every team's fighters stand on
 * the two native roster rows (five slots each). Pure functions without
 * globals: the game, the online room and a host unit test
 * (port/tests/tag_squad.c) share them. Teams are 0..4 here, shown as 1..5. */
#define TAG_SQUAD_TEAMS 5
#define TAG_SQUAD_ROW 5
#define TAG_SQUAD_FIGHTERS 10

/* 1 when the row-0 teams of partition a (bit t = team t) come before those of
   b: the lists of team numbers are compared in order, and a list that is the
   beginning of the other comes first. */
static inline int TagSquad_Before(int a, int b) {
    for (;;) {
        int la = a & -a, lb = b & -b;
        if (!la) return 1;
        if (!lb) return 0;
        if (la != lb) return la < lb;
        a &= a - 1;
        b &= b - 1;
    }
}

/* teams: 2..5; size[t]: 1..5 fighters of team t, at most ten in total.
 * Out: rowCount[r] = fighters on row r, slotTeam[r][m] = team of every slot
 * (-1 unused). Returns 1, or 0 for sizes that are not allowed.
 *  1. Team 0 starts at row 0, slot 0. Teams ascend inside a row and every
 *     team is one block per row.
 *  2. No team is split when the teams can be parted into two rows of at
 *     most five fighters, both in use. Of those partitions the one with the
 *     smallest difference between the rows wins; equal ones go to the row 0
 *     that lists the lower team numbers (TagSquad_Before).
 *  3. Otherwise exactly one team stands on both rows: the highest-numbered
 *     team that can fill row 0 to five and put its remainder on row 1 while
 *     the other teams are parted as in rule 2. Its fighters are the last of
 *     both rows.
 * Slot (0,0) and slot (1,0) are always on different teams. */
static inline int TagSquad_Layout(int teams, const int size[TAG_SQUAD_TEAMS], int rowCount[2],
                                  signed char slotTeam[2][TAG_SQUAD_ROW]) {
    int total = 0, t, mask, best = -1, bestDiff = 99, split = -1, head = 0, r, m;
    for (r = 0; r < 2; r++) {
        rowCount[r] = 0;
        for (m = 0; m < TAG_SQUAD_ROW; m++) slotTeam[r][m] = -1;
    }
    if (teams < 2 || teams > TAG_SQUAD_TEAMS) return 0;
    for (t = 0; t < teams; t++) {
        if (size[t] < 1 || size[t] > TAG_SQUAD_ROW) return 0;
        total += size[t];
    }
    if (total > TAG_SQUAD_FIGHTERS) return 0;
    for (mask = 1; mask < (1 << teams); mask += 2) { /* (odd: team 0 is on row 0) */
        int a = 0, diff;
        for (t = 0; t < teams; t++) if (mask >> t & 1) a += size[t];
        if (a > TAG_SQUAD_ROW || total - a > TAG_SQUAD_ROW || total - a < 1) continue;
        diff = 2 * a > total ? 2 * a - total : total - 2 * a;
        if (diff < bestDiff || (diff == bestDiff && TagSquad_Before(mask, best))) {
            best = mask;
            bestDiff = diff;
        }
    }
    if (best < 0) {
        for (split = teams - 1; split >= 1; split--) {
            for (mask = 1; mask < (1 << teams); mask += 2) {
                int a = 0, k;
                if (mask >> split & 1) continue;
                for (t = 0; t < teams; t++) if (mask >> t & 1) a += size[t];
                k = TAG_SQUAD_ROW - a; /* the split team's fighters on row 0 */
                if (k < 1 || k > size[split] - 1) continue;
                if (best < 0 || TagSquad_Before(mask, best)) {
                    best = mask;
                    head = k;
                }
            }
            if (best >= 0) break;
        }
        if (best < 0) return 0;
    }
    for (t = 0; t < teams; t++) {
        if (t == split) continue;
        r = (best >> t & 1) ? 0 : 1;
        for (m = 0; m < size[t]; m++) slotTeam[r][rowCount[r]++] = (signed char)t;
    }
    if (split >= 0) {
        for (m = 0; m < size[split]; m++) {
            r = m < head ? 0 : 1;
            slotTeam[r][rowCount[r]++] = (signed char)split;
        }
    }
    return 1;
}

/* Player seats: in player order every player takes the next free slot of the
 * chosen team, row 0 before row 1, so the players are the first fighters of
 * their team. slotOwner[r][m]: the player, or -1 for a CPU fighter. Returns 0
 * when a team is asked to seat more players than it has fighters (the extra
 * players stay without a seat). */
static inline int TagSquad_Seat(signed char slotTeam[2][TAG_SQUAD_ROW], int players, const int playerTeam[4],
                                signed char slotOwner[2][TAG_SQUAD_ROW]) {
    int p, r, m, ok = 1;
    for (r = 0; r < 2; r++) for (m = 0; m < TAG_SQUAD_ROW; m++) slotOwner[r][m] = -1;
    for (p = 0; p < players && p < 4; p++) {
        int seated = 0;
        for (r = 0; r < 2 && !seated; r++) for (m = 0; m < TAG_SQUAD_ROW && !seated; m++) {
            if (slotTeam[r][m] == playerTeam[p] && slotOwner[r][m] < 0) {
                slotOwner[r][m] = (signed char)p;
                seated = 1;
            }
        }
        if (!seated) ok = 0;
    }
    return ok;
}
#endif
