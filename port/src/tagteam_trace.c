#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "battle/tag_capacity.h"
extern uint64_t SDL_GetTicksNS(void);
unsigned Port_LoadTimeUs(void) { return (unsigned)(SDL_GetTicksNS()/1000); }
void Port_ModelRequestTrace(int actor,int kind,int chara,int costume,int variant) {
    if(getenv("BT3_LOAD_TRACE"))
        fprintf(stderr,"model load: actor=%d kind=%d character=%d costume=%d variant=%d\n",actor,kind,chara,costume,variant);
}
int Port_FastFileQueue(void) {
    extern int Port_NetSession(void);
    /* The legacy step cadence remains available for comparison, and for the
       upstream network protocol whose simulation includes loader states. */
    return getenv("BT3_TAG_TEAM") != NULL && !Port_NetSession() &&
           getenv("BT3_TAG_LEGACY_LOADING") == NULL;
}
void Port_LoadTrace(int point) {
    static uint64_t start;
    static unsigned serial;
    if (!getenv("BT3_LOAD_TRACE")) return;
    if (point==0) { start=SDL_GetTicksNS(); ++serial; }
    fprintf(stderr,"tagload batch=%u point=%d elapsed_ms=%u\n",serial,point,
            (unsigned)((SDL_GetTicksNS()-start)/1000000));
}
int Port_TagAvailable(void) {
    extern int Port_NetSession(void);
    return getenv("BT3_TAG_TEAM")!=NULL && !Port_NetSession();
}
void Port_TagViewTrace(int role,int actor,int control,int views,int shared,int owner,int practice) {
    static unsigned tick;
    if(getenv("BT3_TAG_CAMERA_TRACE") && ++tick%120==0)
        fprintf(stderr,"online-view role=%d actor=%d control=%d views=%d shared=%d owner=%d practice=%d\n",role,actor,control,views,shared,owner,practice);
}
void Port_TagMenuTrace(int page,int a,int b,int c,int d,int e) {
    static int last[6]={-1,-1,-1,-1,-1,-1};
    extern unsigned gPortVBlanks;
    extern unsigned gGsFrame;
    if(!getenv("BT3_TAG_MENU_TEST")) return;
    if(last[0]==page && last[1]==a && last[2]==b && last[3]==c && last[4]==d && last[5]==e) return;
    last[0]=page;last[1]=a;last[2]=b;last[3]=c;last[4]=d;last[5]=e;
    fprintf(stderr,"tagmenu frame=%u page=%d state=%d,%d,%d,%d,%d draw=%u\n",gPortVBlanks,page,a,b,c,d,e,gGsFrame);
}

void Port_TagCpuPromptTrace(int event,int slot,int level) {
    if(getenv("BT3_TAG_MENU_TEST"))
        fprintf(stderr,"tagcpu prompt=%d slot=%d level=%d\n",event,slot,level);
}

void Port_TagTeamTrace(int frame, int fighter, int chara, int team, int target, int hp, int action) {
    if (getenv("BT3_TAG_TRACE")) {
        fprintf(stderr, "tagteam frame=%d fighter=%d chara=%d team=%d target=%d hp=%d action=%d\n",
                frame, fighter, chara, team, target, hp, action);
    }
}

/* High-water marks of the capacities whose overrun ends the program: 0 the bytes of one frame's display list,
   1 the bytes and 2 the blocks held by the effect pools, 3 the file requests in the queue. They describe this
   run and are not game state (a rollback does not take them back). */
static int sMarks[4], sMarkLimits[4];
void Port_TagMark(int kind, int value, int limit) {
    if ((unsigned)kind < 4 && value > sMarks[kind]) {
        sMarks[kind] = value;
        sMarkLimits[kind] = limit;
    }
}
static void marks_text(char *out, size_t size) {
    snprintf(out, size, "display_list=%d/%d effect_pool_bytes=%d/%d effect_pool_blocks=%d file_requests=%d/%d",
             sMarks[0], sMarkLimits[0], sMarks[1], sMarkLimits[1], sMarks[2], sMarks[3], sMarkLimits[3]);
}
/* End of a battle: BT3_TAG_TRACE logs the marks; the next battle starts from zero. */
void Port_TagMarksReport(int fighters) {
    char text[200];
    if (getenv("BT3_TAG_TRACE")) {
        marks_text(text, sizeof(text));
        fprintf(stderr, "tagmarks fighters=%d %s\n", fighters, text);
    }
    memset(sMarks, 0, sizeof(sMarks));
}

/* The native build ends itself: not a fault, so the crash handler never sees it. Write the same file a crash
   writes (plat_crash.c), with the reason in words, and end. No window: a headless or hidden run must not wait. */
extern void Port_CrashReport(const char *reason, const char *detail);
static void fatal(const char *message, const char *numbers) {
    char marks[200], detail[400];
    marks_text(marks, sizeof(marks));
    snprintf(detail, sizeof(detail), "%s%shigh-water marks of this battle: %s", numbers, numbers[0] ? "\n" : "", marks);
    fprintf(stderr, "Native Tag Team stopped: %s\n", message);
    Port_CrashReport(message, detail);
    exit(2);
}
void Port_TagTeamFatal(const char *message) {
    fatal(message, "");
}
/* A capacity check failed: what was asked for, what was in use and the limit go into the report. */
void Port_TagCapacityFatal(const char *message, int wanted, int used, int limit) {
    char numbers[120];
    snprintf(numbers, sizeof(numbers), "wanted %d, in use %d, capacity %d", wanted, used, limit);
    fatal(message, numbers);
}

/* A match of three or more teams is decided (BT3_TAG_TRACE). kind 1: one team's sums (team, health, full health,
   living fighters); kind 0: the decision (time over or knock-out, the winning team or -1 for a draw, the fighter
   that represents it, the number of teams). */
void Port_TagDecidedTrace(int kind,int a,int b,int c,int d) {
    if(!getenv("BT3_TAG_TRACE")) return;
    if(kind) fprintf(stderr,"tagdecided team=%d health=%d full=%d living=%d\n",a,b,c,d);
    else fprintf(stderr,"tagdecided reason=%s winner_team=%d actor=%d teams=%d\n",a?"time":"ko",b,c,d);
}

void Port_TagInputTrace(int actor,int pad,unsigned pressed,int action) {
    static int previous[TAG_ACTOR_CAPACITY];
    if(getenv("BT3_TAG_INPUT_TRACE") && (pressed || previous[actor]!=action))
        fprintf(stderr,"taginput actor=%d pad=%d pressed=%08x action=%d\n",actor,pad,pressed,action);
    previous[actor]=action;
}

void Port_TagObjectTrace(int view,int actor,unsigned flags,unsigned ptr) {
    extern unsigned gPortVBlanks;
    if(getenv("BT3_TAG_RENDER_TRACE") && gPortVBlanks%150==0) {
        const unsigned *p=(const unsigned *)(uintptr_t)ptr;
        fprintf(stderr,"tagrender tick=%u view=%d actor=%d flags=%08x data=%08x,%08x,%08x,%08x\n",gPortVBlanks,view,actor,flags,p[1],p[2],p[3],p[4]);
    }
}

int Port_TagReviveTest(void) { return getenv("BT3_TAG_TEST_REVIVE")!=NULL; }
int Port_TagLobbyTest(void) { const char *v=getenv("BT3_TAG_TEST_LOBBY");return v?atoi(v):0; }
int Port_TagChallengeTest(void) { const char *v=getenv("BT3_TAG_TEST_CHALLENGE");return v?atoi(v):0; }
int Port_TagChallengeSkipTest(void) { return getenv("BT3_TAG_TEST_WAVE_SKIP")!=NULL; }
int Port_TagChallengeFinishTest(void) { return getenv("BT3_TAG_TEST_WAVE_FINISH")!=NULL; }
int Port_TagTournamentTest(void) { return getenv("BT3_TAG_TEST_TOURNAMENT")!=NULL; }
int Port_TagModeRushTest(void) { const char *v=getenv("BT3_TAG_TEST_MODE_RUSH");return v?atoi(v):0; }
int Port_TagModeRushViews(void) { const char *v=getenv("BT3_TAG_PLAY");return v?atoi(v):0; }
int Port_TagAudioTest(void) { return getenv("BT3_TAG_TEST_AUDIO")!=NULL; }
int Port_TagClashTest(void) { return getenv("BT3_TAG_TEST_CLASH")!=NULL; }
int Port_TagControlsTest(void) { const char *v=getenv("BT3_TAG_TEST_CONTROLS");return v?atoi(v):0; }
int Port_TagMultiBeamTest(void) { return getenv("BT3_TAG_TEST_MULTI_BEAMS")!=NULL; }
int Port_TagBeamAssistTest(void) { return getenv("BT3_TAG_TEST_BEAM_ASSIST")!=NULL; }
void Port_TagAssistTrace(int actor,int state,int action,int tick) {
    if(getenv("BT3_TAG_TEST_BEAM_ASSIST"))
        fprintf(stderr,"tagassist actor=%d state=%d action=%x tick=%d\n",actor,state,action,tick);
}
int Port_TagShowcase(void) {const char *v=getenv("BT3_TAG_SHOWCASE");return v?atoi(v):0;}
void Port_TagShowcaseFrame(int tick) {
    extern unsigned gGsFrame;
    if(getenv("BT3_TAG_SHOWCASE"))fprintf(stderr,"showcase-frame tick=%d frame=%u\n",tick,gGsFrame);
}
int Port_TagShowcaseDelay(void) {const char *v=getenv("BT3_TAG_SHOWCASE_DELAY");return v?atoi(v):15;}
int Port_TagShowcaseDistance(void) {const char *v=getenv("BT3_TAG_SHOWCASE_DISTANCE");int d=v?atoi(v):150;return d<40?40:d;}
void Port_TagShowcaseView(float *eye,float *look) {
    const char *v=getenv("BT3_TAG_SHOWCASE_CAMERA");
    if(v) sscanf(v,"%f,%f,%f,%f,%f,%f",eye,eye+1,eye+2,look,look+1,look+2);
}
int Port_TagShowcaseLead(int actor,int fallback) {
    const char *v=getenv(actor?"BT3_TAG_SHOWCASE_OPPONENT":"BT3_TAG_SHOWCASE_LEAD");
    return v?atoi(v):fallback;
}
int Port_TagShowcaseSlot(int actor) {
    const char *v=getenv(actor?"BT3_TAG_SHOWCASE_SLOT1":"BT3_TAG_SHOWCASE_SLOT0");
    return v?atoi(v):actor?4:2;
}
int Port_TagBeamTest(void) { return getenv("BT3_TAG_TEST_BEAMS")!=NULL || Port_TagShowcase(); }
int Port_TagCameraTest(void) { const char *v=getenv("BT3_TAG_TEST_CAMERAS");return v?atoi(v):0; }
int Port_TagContactTest(void) { const char *v=getenv("BT3_TAG_TEST_CONTACT");return v?atoi(v):0; }
int Port_TagFusionTest(void) { const char *v=getenv("BT3_TAG_TEST_FUSION");return v?atoi(v):0; }
int Port_TagFusionPair(int which) {
    int a=3,b=34,c=0;
    const char *v=getenv("BT3_TAG_FUSION_PAIR");
    if(v) sscanf(v,"%d,%d,%d",&a,&b,&c);
    return which==0?a:which==1?b:c;
}
int Port_TagFusionDouble(void) { return getenv("BT3_TAG_FUSION_DOUBLE")!=NULL; }
/* BT3_TAG_TEST_DEFUSE_BREAK=<mode>[,<count>]: in the update that requests a timed fusion's power-down, bring
   another decision too. Mode 1 taps a button on the pad that controls the fused fighter, mode 2 queues another
   action; count is the number of requests to break (default 1, -1 = every one). */
int Port_TagDefuseBreak(int which) {
    int mode=0,count=1;
    const char *v=getenv("BT3_TAG_TEST_DEFUSE_BREAK");
    if(v) sscanf(v,"%d,%d",&mode,&count);
    return which?count:mode;
}
/* event: 0 periodic, 1 power-down requested, 2 request lost (back to the timed state), 3 forced, 4 separated. */
void Port_TagFusionTrace(int tick,int actor,int event,int state,int ticks,int action,int overdue) {
    if(getenv("BT3_TAG_TRACE") || getenv("BT3_TAG_TEST_DEFUSE_BREAK"))
        fprintf(stderr,"tagfusion tick=%d actor=%d event=%d state=%d ticks=%d action=%x overdue=%d\n",
                tick,actor,event,state,ticks,action,overdue);
}
int Port_TagFusionKo(void) { return getenv("BT3_TAG_FUSION_KO")!=NULL; }
int Port_TagFusionRematch(void) { return getenv("BT3_TAG_FUSION_REMATCH")!=NULL; }
int Port_TagGiantTest(void) { return getenv("BT3_TAG_TEST_GIANTS")!=NULL; }
int Port_TagCpuTest(void) { return getenv("BT3_TAG_TEST_CPU")!=NULL; }
/* BT3_TAG_TEST_SQUAD=<case>: 1 what a match of three teams offers, the session and the fallen player's view;
   2 revive, 3 takeover, 4 fusion, 5 beam assist, 6 Outnumbered, each with the fighters named by
   BT3_TAG_TEST_SQUAD_ACTORS=a,b,c,d (what they stand for is written at each case in tag_team_test.c). */
int Port_TagSquadTest(void) { const char *v=getenv("BT3_TAG_TEST_SQUAD"); return v?(atoi(v)>0?atoi(v):1):0; }
static int list_value(const char *name,int which) {
    int v[TAG_ACTOR_CAPACITY],n,k=0;
    const char *s=getenv(name);
    for(n=0;n<TAG_ACTOR_CAPACITY;n++) v[n]=-1;
    while(s && *s && k<TAG_ACTOR_CAPACITY) {
        v[k++]=atoi(s);
        s=strchr(s,',');
        if(s) s++;
    }
    return (unsigned)which<TAG_ACTOR_CAPACITY?v[which]:-1;
}
int Port_TagSquadActor(int which) { return list_value("BT3_TAG_TEST_SQUAD_ACTORS",which); }
/* BT3_TAG_TEST_SEATS=f,f,...: the fighter each player of a demo match controls (player 1 first). */
int Port_TagTestSeat(int player) { return list_value("BT3_TAG_TEST_SEATS",player); }
/* BT3_TAG_TEST_CAST=f:c,f:c,...: the character of single fighters of a demo match (-1: the demo's own). */
int Port_TagTestCast(int fighter) {
    const char *s=getenv("BT3_TAG_TEST_CAST");
    while(s && *s) {
        int f=-1,c=-1;
        if(sscanf(s,"%d:%d",&f,&c)==2 && f==fighter) return c;
        s=strchr(s,',');
        if(s) s++;
    }
    return -1;
}
void Port_TagTestNote(int id,int a,int b,int c,int d) {
    fprintf(stderr,"tagteam fixture note id=%d values=%d,%d,%d,%d\n",id,a,b,c,d);
}
/* BT3_TAG_HIT_TRACE: every hit that takes health, with the fighter that owns it and both teams. The counts are
   read by the fixtures only; they describe this run and are not game state. */
static int sHits[TAG_ACTOR_CAPACITY][TAG_ACTOR_CAPACITY];
void Port_TagHitTrace(int victim,int source,int lost,int victimTeam,int sourceTeam) {
    static int enabled=-1;
    if(enabled<0) enabled=getenv("BT3_TAG_HIT_TRACE")!=NULL;
    if(!enabled || lost<=0) return;
    if((unsigned)victim<TAG_ACTOR_CAPACITY && (unsigned)source<TAG_ACTOR_CAPACITY) sHits[source][victim]++;
    fprintf(stderr,"taghit victim=%d source=%d lost=%d teams=%d,%d\n",victim,source,lost,victimTeam,sourceTeam);
}
int Port_TagHitCount(int source,int victim) {
    return (unsigned)victim<TAG_ACTOR_CAPACITY && (unsigned)source<TAG_ACTOR_CAPACITY?sHits[source][victim]:0;
}
/* BT3_TAG_BALANCE_TRACE: the numbers the Outnumbered help uses for a fighter, whenever they change: its own
   living team, the enemy count it is compared with, damage dealt and taken in percent. */
void Port_TagBalanceTrace(int actor,int team,int own,int enemy,int dealt,int taken) {
    static int enabled=-1,last[TAG_ACTOR_CAPACITY][4];
    if(enabled<0) enabled=getenv("BT3_TAG_BALANCE_TRACE")!=NULL;
    if(!enabled || (unsigned)actor>=TAG_ACTOR_CAPACITY) return;
    if(last[actor][0]==own && last[actor][1]==enemy && last[actor][2]==dealt && last[actor][3]==taken) return;
    last[actor][0]=own;last[actor][1]=enemy;last[actor][2]=dealt;last[actor][3]=taken;
    fprintf(stderr,"tagbalance actor=%d team=%d own=%d enemy=%d dealt=%d taken=%d\n",actor,team,own,enemy,dealt,taken);
}
int Port_TagStageTest(void) { const char *v=getenv("BT3_TAG_TEST_STAGE"); return v?atoi(v):0; }
int Port_TagSpawnTest(void) { return getenv("BT3_TAG_TEST_SPAWN")!=NULL; }
void Port_TagSpawnFailure(int stage,int actor,int grounded,int clearBody) {
    fprintf(stderr,"tagspawn failed stage=%d actor=%d grounded=%d clear=%d\n",stage,actor,grounded,clearBody);
}
void Port_TagSpawnTrace(int tick,int actor,unsigned ptr) {
    extern unsigned gGsFrame;
    const float *p=(const float *)(uintptr_t)ptr;
    fprintf(stderr,"tagspawn tick=%d actor=%d pos=%.3f,%.3f,%.3f frame=%u\n",tick,actor,p[0],p[1],p[2],gGsFrame);
}
int Port_TagCinemaTest(void) { const char *v=getenv("BT3_TAG_TEST_CINEMA"); return v?atoi(v):0; }
void Port_TagSpecialTrace(int tick,int flags,int frozen,int visible,int action) {
    extern unsigned gGsFrame;
    fprintf(stderr,"tagspecial tick=%d flags=%x bystanderFrozen=%d visible=%d action=%x frame=%u\n",
            tick,flags,frozen,visible,action,gGsFrame);
}
void Port_TagMotionTrace(int tick,int actor,unsigned ptr) {
    const int *v=(const int *)(uintptr_t)ptr;
    fprintf(stderr,"tagmotion tick=%d actor=%d anim=%d time=%.1f action=%x frozen=%d end=%d work=%d,%d,%d,%d tech=%x steps=%d partnerStep=%d partner=%d reload=%d,%d,%d pair=%d,%d\n",
        tick,actor,v[0],*(const float *)&v[1],v[2],v[3],v[4],v[5],v[6],v[7],v[8],v[9],v[10],v[11],v[12],v[13],v[14],v[15],v[16],v[17]);
}
int Port_TagResultTest(void) { const char *v=getenv("BT3_TAG_TEST_RESULT"); return v?atoi(v):0; }
void Port_TagStageProbe(int phase, int stage, unsigned ptr) {
    const float *v=(const float *)(uintptr_t)ptr;
    fprintf(stderr,"tagstageprobe phase=%d stage=%d scale=%.3f radius=%.3f top=%.3f bottom=%.3f water=%.3f ground=%.3f\n",
            phase,stage,v[0],v[1],v[2],v[3],v[4],v[5]);
}
void Port_TagPostTrace(int kind,int view,int split,unsigned ptr) {
    extern unsigned gPortVBlanks;
    const int *r=(const int *)(uintptr_t)ptr;
    if(getenv("BT3_TAG_POST_TRACE") && gPortVBlanks%30==0)
        fprintf(stderr,"tagpost frame=%u kind=%d view=%d split=%d rect=%d,%d,%d,%d\n",
                gPortVBlanks,kind,view,split,r[0],r[1],r[2],r[3]);
}
void Port_TagPanTrace(int view,unsigned ptr) {
    extern unsigned gPortVBlanks;
    const float *p=(const float *)(uintptr_t)ptr;
    if(getenv("BT3_TAG_POST_TRACE") && gPortVBlanks%120==0)
        fprintf(stderr,"tagpan frame=%u view=%d speed=%.3f strength=%.3f camera=%.3f,%.3f\n",
                gPortVBlanks,view,p[0],p[1],p[2],p[3]);
}
void Port_TagCpuTrace(int actor,int old,int target,int damage) {
    if(getenv("BT3_TAG_CPU_TRACE"))
        fprintf(stderr,"tagcpu actor=%d old=%d target=%d grudge=%d\n",actor,old,target,damage);
}
int Port_TagFusionResult(void) {
    const char *s=getenv("BT3_TAG_FUSION_RESULT");
    return s?atoi(s):53;
}
int Port_TagFusionSeat(int which) {
    int a=0,b=2;
    const char *s=getenv("BT3_TAG_FUSION_SEATS");
    if(s) sscanf(s,"%d,%d",&a,&b);
    return which?b:a;
}
/* Opt-in weather probe observes the real draw path, particle banks and clocks. */
void Port_TagWeatherTrace(unsigned epoch,int view,unsigned particles,unsigned tracker,int count,int move) {
    static int enabled=-1;
    extern unsigned gPortVBlanks;
    unsigned hash=2166136261u;
    const unsigned char *p=(const unsigned char *)(uintptr_t)particles;
    if(enabled<0) enabled=getenv("BT3_TAG_WEATHER_TRACE")!=NULL;
    if(!enabled) return;
    for(int i=0;i<count*64;i++) hash=(hash^p[i])*16777619u;
    fprintf(stderr,"weather frame=%u epoch=%u view=%d bank=%x tracker=%x count=%d move=%d hash=%x\n",
            gPortVBlanks,epoch,view,particles,tracker,count,move,hash);
}
void Port_TagBeamTrace(int actor,int phase,int flags,int expire,void *a,void *b) {
    static unsigned n[10];
    if(getenv("BT3_TAG_BEAM_TRACE") && actor>=0 && actor<10 && (++n[actor]%15)==0) {
        float *p=a,*q=b;
        fprintf(stderr,"beam actor=%d phase=%d flags=%x expire=%d muzzle=%.1f,%.1f,%.1f head=%.1f,%.1f,%.1f\n",actor,phase,flags,expire,p[0],p[1],p[2],q[0],q[1],q[2]);
    }
}
void Port_TagIntroTrace(int actor,int chara,int line,int state) {
    if(getenv("BT3_TAG_TRACE")) fprintf(stderr,"tagintro actor=%d chara=%d line=%d state=%d\n",actor,chara,line,state);
}
void Port_TagFaceTrace(unsigned obj,int mode,int line,int time,int shape,int first,int count,float jaw) {
    static int enabled=-1;
    extern unsigned gPortVBlanks;
    if(enabled<0)enabled=getenv("BT3_TAG_FACE_TRACE")!=NULL;
    if(enabled && (mode || (gPortVBlanks%30)==0))
        fprintf(stderr,"tagface frame=%u obj=%x mode=%d line=%d time=%d shape=%d first=%d count=%d jaw=%.4f\n",
            gPortVBlanks,obj,mode,line,time,shape,first,count,jaw);
}
void Port_TagClashTrace(int tick,int actor,int player,int obj,int action) {
    fprintf(stderr,"clash tick=%d actor=%d player=%d obj=%d action=%x\n",tick,actor,player,obj,action);
}
void Port_TagTestState(int action,int hp,int stocks,int progress) {
    fprintf(stderr,"tagteam fixture state action=%d hp=%d rescuerStocks=%d progress=%d\n",action,hp,stocks,progress);
}
void Port_TagTestPositions(unsigned a,unsigned b) {
    const float *p=(const float *)(uintptr_t)a,*q=(const float *)(uintptr_t)b;
    fprintf(stderr,"tagteam fixture positions %.3f %.3f %.3f / %.3f %.3f %.3f\n",p[0],p[1],p[2],q[0],q[1],q[2]);
}
void Port_TagTestCheck(int pass,int check) {
    fprintf(stderr,"tagteam fixture: %s check=%d\n",pass?"PASS":"FAIL",check);
    if(!pass) exit(3);
    if(check==99) {
        if(!getenv("BT3_TAG_ONLINE")) exit(0);
        else {extern void TagOnline_TestDone(void);TagOnline_TestDone();}
    }
}

void Port_TagTeamControlTrace(int fighter, int control, int inject, int freeze, int side) {
    if (getenv("BT3_TAG_DEBUG")) {
        fprintf(stderr, "tagteam control fighter=%d control=%d inject=%d freeze=%d side=%d\n", fighter, control, inject, freeze, side);
    }
}

int Port_TagSpecialCharacter(void) { const char *v=getenv("BT3_TAG_SPECIAL_CHARACTER");return v?atoi(v):-1; }
int Port_TagSpecialSlot(void) { const char *v=getenv("BT3_TAG_SPECIAL_SLOT");return v?atoi(v):-1; }
