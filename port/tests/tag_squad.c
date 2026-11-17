/* Layout contract of Team Battle with three to five teams: every size vector
   of 2..5 teams with 1..5 fighters and at most ten in total. The checks below
   find the best partition on their own, by listing every one, and compare it
   with what TagSquad_Layout built.
     gcc -std=c11 -Wall -Wextra -o tag_squad port/tests/tag_squad.c && ./tag_squad */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../../include/battle/tag_squad.h"

static int vectors, splits, refused;

/* Row-0 team lists of two partitions, compared number by number. */
static int list_before(const int *a, int na, const int *b, int nb) {
    int i;
    for (i = 0; i < na && i < nb; i++) if (a[i] != b[i]) return a[i] < b[i];
    return na <= nb;
}

/* Every way of putting whole teams on the two rows: the best one by rule 2. */
static int best_whole(int teams, const int *size, int *bestList, int *bestCount, int *bestDiff) {
    int mask, found = 0, total = 0, t;
    for (t = 0; t < teams; t++) total += size[t];
    for (mask = 0; mask < (1 << teams); mask++) {
        int a = 0, n = 0, list[5], diff;
        if (!(mask & 1)) continue; /* rule 1: team 0 opens row 0 */
        for (t = 0; t < teams; t++) if (mask >> t & 1) { a += size[t]; list[n++] = t; }
        if (a < 1 || a > 5 || total - a < 1 || total - a > 5) continue;
        diff = a > total - a ? a - (total - a) : (total - a) - a;
        if (!found || diff < *bestDiff || (diff == *bestDiff && list_before(list, n, bestList, *bestCount))) {
            found = 1;
            *bestDiff = diff;
            *bestCount = n;
            memcpy(bestList, list, sizeof(list));
        }
    }
    return found;
}

/* Can team s stand on both rows (row 0 full, its fighters last, at least one on each row)? Best row-0 list. */
static int best_split(int teams, const int *size, int s, int *bestList, int *bestCount, int *bestHead) {
    int mask, found = 0, t;
    for (mask = 0; mask < (1 << teams); mask++) {
        int a = 0, n = 0, list[5], k;
        if (!(mask & 1) || (mask >> s & 1)) continue;
        for (t = 0; t < teams; t++) if (mask >> t & 1) { a += size[t]; list[n++] = t; }
        k = 5 - a;
        if (k < 1 || k > size[s] - 1) continue;
        if (!found || list_before(list, n, bestList, *bestCount)) {
            found = 1;
            *bestCount = n;
            *bestHead = k;
            memcpy(bestList, list, sizeof(list));
        }
    }
    return found;
}

static void check(int teams, const int *size) {
    int rowCount[2], r, m, t, total = 0, have[5] = {0}, rows[5] = {0}, both = 0, split = -1;
    int list[5], count = 0, diff = 0, head = 0, whole;
    signed char slot[2][5];
    for (t = 0; t < teams; t++) total += size[t];
    assert(TagSquad_Layout(teams, size, rowCount, slot) == 1);
    vectors++;
    /* both rows hold 1..5 fighters, and together all of them */
    assert(rowCount[0] >= 1 && rowCount[0] <= 5 && rowCount[1] >= 1 && rowCount[1] <= 5);
    assert(rowCount[0] + rowCount[1] == total);
    for (r = 0; r < 2; r++) for (m = 0; m < 5; m++) {
        if (m >= rowCount[r]) { assert(slot[r][m] == -1); continue; }
        assert(slot[r][m] >= 0 && slot[r][m] < teams);
        have[(int)slot[r][m]]++;
        rows[(int)slot[r][m]] |= 1 << r;
    }
    /* every team has exactly its size; at most one team is on both rows */
    for (t = 0; t < teams; t++) {
        assert(have[t] == size[t]);
        if (rows[t] == 3) { both++; split = t; }
    }
    assert(both <= 1);
    /* the two fighters that open the native intro are on different teams; team 0 opens row 0 */
    assert(slot[0][0] == 0 && slot[1][0] != slot[0][0]);
    /* one block per team and row; whole teams ascend; the split team is last on both rows */
    for (r = 0; r < 2; r++) for (m = 1; m < rowCount[r]; m++) {
        int a = slot[r][m - 1], b = slot[r][m];
        if (a == b) continue;
        assert(a != split);
        assert(b == split || a < b);
    }
    whole = best_whole(teams, size, list, &count, &diff);
    if (whole) {
        int at = 0, d = rowCount[0] > rowCount[1] ? rowCount[0] - rowCount[1] : rowCount[1] - rowCount[0];
        /* a team is split only when no whole partition exists */
        assert(both == 0);
        assert(d == diff);
        for (t = 0; t < count; t++) for (m = 0; m < size[list[t]]; m++) assert(slot[0][at++] == list[t]);
        assert(at == rowCount[0]);
    } else {
        int at = 0, s;
        assert(both == 1 && split >= 1);
        splits++;
        /* no higher-numbered team could have been the split one */
        for (s = teams - 1; s > split; s--) assert(!best_split(teams, size, s, list, &count, &head));
        assert(best_split(teams, size, split, list, &count, &head));
        assert(rowCount[0] == 5);
        for (t = 0; t < count; t++) for (m = 0; m < size[list[t]]; m++) assert(slot[0][at++] == list[t]);
        for (m = 0; m < head; m++) assert(slot[0][at++] == split);
        assert(at == 5);
        assert(slot[1][rowCount[1] - 1] == split);
    }
    /* seats: the players of a team are its first fighters (row 0 first), in player order */
    {
        int playerTeam[4], p, need[5] = {0}, fits = 1;
        signed char owner[2][5];
        for (p = 0; p < 4; p++) { playerTeam[p] = p % teams; need[p % teams]++; }
        for (t = 0; t < teams; t++) if (need[t] > size[t]) fits = 0;
        assert(TagSquad_Seat(slot, 4, playerTeam, owner) == fits);
        for (t = 0; t < teams; t++) {
            int cpuSeen = 0, last = -1, seated = 0;
            for (r = 0; r < 2; r++) for (m = 0; m < 5; m++) {
                if (slot[r][m] != t) continue;
                if (owner[r][m] < 0) { cpuSeen = 1; continue; }
                assert(!cpuSeen && owner[r][m] > last && playerTeam[(int)owner[r][m]] == t);
                last = owner[r][m];
                seated++;
            }
            assert(seated == (need[t] < size[t] ? need[t] : size[t]));
        }
        for (r = 0; r < 2; r++) for (m = 0; m < 5; m++) if (slot[r][m] < 0) assert(owner[r][m] == -1);
    }
}

static void expect(int teams, int a, int b, int c, int d, int e, const char *want) {
    int size[5] = {a, b, c, d, e}, rowCount[2], r, m, n = 0;
    signed char slot[2][5];
    char got[32];
    assert(TagSquad_Layout(teams, size, rowCount, slot));
    for (r = 0; r < 2; r++) {
        for (m = 0; m < rowCount[r]; m++) got[n++] = (char)('1' + slot[r][m]);
        if (!r) got[n++] = '/';
    }
    got[n] = 0;
    if (strcmp(got, want)) {
        printf("layout of %d teams %d-%d-%d-%d-%d is %s, expected %s\n", teams, a, b, c, d, e, got, want);
        assert(0);
    }
}

static void each(int teams, int index, int *size, int total) {
    int n;
    if (index == teams) { check(teams, size); return; }
    for (n = 1; n <= 5; n++) {
        if (total + n > 10) break;
        size[index] = n;
        each(teams, index + 1, size, total + n);
    }
}

int main(void) {
    int size[5], rowCount[2], teams;
    signed char slot[2][5];
    for (teams = 2; teams <= 5; teams++) {
        int before = vectors;
        each(teams, 0, size, 0);
        printf("%d teams: %d size vectors\n", teams, vectors - before);
    }
    /* the examples of the design */
    expect(3, 3, 3, 3, 0, 0, "11133/2223");
    expect(5, 2, 2, 2, 2, 2, "11225/33445");
    expect(4, 3, 3, 3, 1, 0, "11133/22243");
    expect(3, 2, 2, 2, 0, 0, "11/2233");
    expect(3, 1, 1, 1, 0, 0, "1/23");
    expect(3, 5, 3, 2, 0, 0, "11111/22233");
    expect(4, 4, 4, 1, 1, 0, "11113/22224");
    expect(3, 4, 4, 2, 0, 0, "11113/22223");
    expect(2, 5, 5, 0, 0, 0, "11111/22222");
    expect(2, 1, 4, 0, 0, 0, "1/2222");
    expect(3, 3, 1, 3, 0, 0, "111/2333");
    /* refused sizes leave both rows empty */
    size[0] = 5; size[1] = 5; size[2] = 1;
    assert(!TagSquad_Layout(3, size, rowCount, slot) && rowCount[0] == 0 && rowCount[1] == 0); refused++;
    size[0] = 0; size[1] = 2; size[2] = 2;
    assert(!TagSquad_Layout(3, size, rowCount, slot)); refused++;
    size[0] = 6; size[1] = 2; size[2] = 2;
    assert(!TagSquad_Layout(3, size, rowCount, slot)); refused++;
    size[0] = 1; size[1] = 1; size[2] = 1; size[3] = 1; size[4] = 1;
    assert(!TagSquad_Layout(6, size, rowCount, slot) && !TagSquad_Layout(1, size, rowCount, slot)); refused += 2;
    printf("tag_squad: %d size vectors checked, %d need a split team, %d bad inputs refused: PASS\n", vectors, splits, refused);
    return 0;
}
