/* Opt-in integration fixture: drives real combat, KO and recovery code. It is
 * dormant unless BT3_TAG_TEST_REVIVE is explicitly set by the test runner. */
#ifdef PORT
#include "common.h"
#include "battle/tag_team.h"
#include "battle/tag_options.h"
#include "battle/tag_session.h"
#include "battle/btl_char_mgr.h"
#include "battle/btl_char_move.h"
#include "battle/btl_seq.h"
#include "battle/tag_fusion.h"
#include "battle/tag_assist.h"
#include "battle/tag_balance.h"
#include "battle/tag_clash.h"
#include "battle/tag_squad.h"
#include "sys/adx.h"
#include "sys/pad.h"
extern s32 Port_TagReviveTest(void);
extern s32 Port_TagAudioTest(void);
extern s32 Port_TagClashTest(void);
extern s32 Port_TagControlsTest(void);
extern s32 Port_TagBeamTest(void);
extern s32 Port_TagCameraTest(void);
extern s32 Port_TagFusionTest(void);
extern s32 Port_TagGiantTest(void);
extern s32 Port_TagCpuTest(void);
extern s32 Port_TagStageTest(void);
extern s32 Port_TagCinemaTest(void),Port_TagResultTest(void);
extern s32 Port_TagSquadTest(void);
extern void TagCinema_MatrixTick(s32);
extern void TagStage_TestTick(s32);
extern void TagCpu_TestTick(s32);
extern void TagGiant_TestTick(s32);
extern void TagFusion_TestTick(s32);
extern void TagCamera_TestTick(s32);
extern void TagBeam_TestTick(s32);
extern void TagControls_TestTick(s32);
extern void TagClash_TestTick(s32);
extern void Port_TagTestCheck(s32, s32);
extern BtlMgrChr *BtlChar_Get(s32);
extern BtlMgrGauge *BtlMember_GetActiveGauge(BtlMgrChr *);
extern s32 BtlMember_Damage(BtlMgrChr *,s32,s32);
extern void BtlAct_Request(BtlMgrChr *,s32), BtlAct_ClearQueue(BtlMgrChr *);
extern void BtlChar_SetHeldFlag(BtlMgrChr *,s32);
extern s32 TagRevive_Progress(s32);
extern s32 TagRevive_Nearby(s32);
extern s32 BtlColl_IsGuarding(BtlMgrChr *);
extern void BtlChar_Place(BtlMgrChr *,Vec4 *,Vec4 *,s32);
extern s32 BtlStage_FindZoneNear(s32,Vec4 *);

static void place(BtlMgrChr *chr,Vec4 pos) {
    Vec4 rot=((BtlMovePose *)&chr->pose)->rot;
    BtlChar_Place(chr,&pos,&rot,BtlStage_FindZoneNear(-1,&pos));
}

/* BT3_TAG_TEST_SEATS: the players of a demo match control the named fighters (asked while the match is set up). */
extern s32 Port_TagTestSeat(s32);
void TagTeam_TestSeats(s32 humans) {
    s32 actor,p;
    if(Port_TagTestSeat(0)<0) return;
    for(actor=0;actor<TagTeam_Count();actor++) TagTeam_SetAssignment(actor,-1);
    for(p=0;p<humans;p++) if((u32)Port_TagTestSeat(p)<(u32)TagTeam_Count()) TagTeam_SetAssignment(Port_TagTestSeat(p),p);
}

static void audio_check(void) {
    extern void BtlCharSnd_ClearRequests(void), BtlCharSnd_PlayRequests(void);
    extern void BtlCharSnd_PlayVoice(BtlMgrChr *,s32), BtlCharSnd_PlayOwn(BtlMgrChr *,s32);
    extern void BtlCharSnd_PlayCommon(BtlMgrChr *,s32), BtlCharSnd_PlayStream(BtlMgrChr *,s32);
    extern void Snd_Update(void), Snd_StopBank(s32), Snd_SetPause(s32,s32);
    extern void BtlScript_StopVoices(void);
    extern s32 Port_TagAudioProbe(s32,s32), Port_TagSampleProbe(s32);
    extern void Port_TagSampleProbeReset(void);
    s32 i,all=0, banks=4,count=TagTeam_Count(),last=count-1;
    for(i=0;i<count;i++) {
        all|=(1<<(4+i)) | (1<<(i<2?2+i:4+PORT_FIGHTER_CAPACITY+i-2));
        banks|=1<<(4+i);
    }
    BtlCharSnd_ClearRequests();
    Port_TagSampleProbeReset();
    for(i=0;i<count;i++) {
        BtlMgrChr *chr=BtlChar_Get(i);
        BtlCharSnd_PlayCommon(chr,0);
        /* More than the console's 32 commands in one ten-fighter frame. */
        BtlCharSnd_PlayCommon(chr,0);
        BtlCharSnd_PlayCommon(chr,0);
        BtlCharSnd_PlayOwn(chr,0);
        BtlCharSnd_PlayVoice(chr,0);
        /* A real, long ADX file also exercises each streamed-effect channel. */
        BtlCharSnd_PlayStream(chr,PortGame_VoiceLine(TagTeam_Side(i)->form.chara,0,0));
    }
    BtlCharSnd_PlayRequests();
    Snd_Update();
    Port_TagTestCheck(Port_TagAudioProbe(all,0),20);
    Port_TagTestCheck(Port_TagSampleProbe(banks),21);
    Adx_PauseSeVoice(); Snd_SetPause(banks,1);
    Port_TagTestCheck(Port_TagAudioProbe(all,1),22);
    Port_TagTestCheck(Port_TagAudioProbe(1,0),23); /* music keeps playing */
    Adx_ResumeSeVoice(); Snd_SetPause(banks,0);
    Port_TagTestCheck(Port_TagAudioProbe(all,0),24);
    Voice_Stop(last); StreamSe_Stop(last); Snd_StopBank(1<<(4+last));
    Port_TagTestCheck(Voice_IsStopped(last)&&StreamSe_IsStopped(last),25);
    Port_TagTestCheck(Port_TagAudioProbe(all&~((1<<(4+last))|(1<<(4+PORT_FIGHTER_CAPACITY+last-2))),0),26);
    BtlScript_StopVoices();
    for(i=0;i<count;i++) Port_TagTestCheck(Voice_IsStopped(i)&&StreamSe_IsStopped(i),30+i);
    Port_TagTestCheck(!Bgm_IsStopped(),34);
    Port_TagTestCheck(1,99);
}

static void check_start_spacing(void) {
        /* Check spacing before the fixture changes positions. */
        s32 a,b;
        extern f32 BtlCharApi_GetRadius(s32),BtlCharApi_GetHeight(s32);
        for(a=0;a<TagTeam_Count();a++) for(b=0;b<a;b++) {
            Vec4 *p=&((BtlMovePose *)&BtlChar_Get(a)->pose)->pos;
            Vec4 *q=&((BtlMovePose *)&BtlChar_Get(b)->pose)->pos;
            s32 ao=BattleSide_GetObjId(a),bo=BattleSide_GetObjId(b);
            f32 x=p->x-q->x,z=p->z-q->z,y=p->y-q->y;
            f32 r=BtlCharApi_GetRadius(ao)+BtlCharApi_GetRadius(bo);
            s32 apart=x*x+z*z>=r*r || y>=BtlCharApi_GetHeight(ao) || -y>=BtlCharApi_GetHeight(bo);
            if(!apart) {
                extern void Port_TagTestPositions(u32,u32);
                extern s32 BtlStage_GetStartPlace(s32,Vec4 *,Vec4 *,s32);
                Vec4 expectedA,expectedB,rotation;
                Port_TagTestPositions((u32)p,(u32)q);
                BtlStage_GetStartPlace(a,&expectedA,&rotation,0);
                BtlStage_GetStartPlace(b,&expectedB,&rotation,0);
                Port_TagTestPositions((u32)&expectedA,(u32)&expectedB);
            }
            Port_TagTestCheck(apart,200+a*10+b);
        }
}

/* Ready releases the CPUs before the Fight sequence begins. On short stages
   they can already reach an opponent before the audio fixture gets its first
   fighting tick, so check the ten initial positions before that release. */
void TagTeam_TestStartSpacing(void) {
    if(Port_TagAudioTest() && TagTeam_Active())check_start_spacing();
}

/* BT3_TAG_TEST_SQUAD with BT3_TAG_TEAMS=2,2,2 and one player (rows 1 1 / 2 2 3 3: fighters 0 and 2 are team 1,
   1 and 3 team 2, 4 and 5 team 3). What is on and off in a match of three teams, and where a fallen player's
   view goes when no takeover is offered: to the living teammate, not to the next fighter by number (an enemy). */
static void squad_test(s32 tick) {
    extern s32 TagRevive_Enabled(void);
    extern int Port_TagOption(int);
    extern void Port_TagOptionSet(int,int);
    static s32 taken;
    if(tick==5) {
        Port_TagTestCheck(TagTeam_TeamCount()==3 && TagTeam_Count()==6 && TagTeam_WinningTeam()==-1,720);
        Port_TagTestCheck(TagTeam_Team(0)==0 && TagTeam_Team(2)==0 && TagTeam_Team(1)==1 && TagTeam_Team(3)==1 &&
            TagTeam_Team(4)==2 && TagTeam_Team(5)==2,721);
        Port_TagTestCheck(TagTeam_Feature(TAG_FEATURE_REVIVE) && TagTeam_Feature(TAG_FEATURE_TAKEOVER) &&
            TagTeam_Feature(TAG_FEATURE_FUSION) && TagTeam_Feature(TAG_FEATURE_ASSIST) &&
            TagTeam_Feature(TAG_FEATURE_OUTNUMBERED),722);
        Port_TagTestCheck(TagRevive_Enabled()==(Port_TagOption(TAG_OPT_REVIVE)!=0) &&
            TagTeam_FusionsEnabled()==(Port_TagOption(TAG_OPT_FUSIONS)!=0),723);
        Port_TagTestCheck(TagTeam_Player(0)==0 && TagTeam_ViewActor(0)==0 && !TagTeam_IsEnemy(0,2) &&
            TagTeam_IsEnemy(0,1) && TagTeam_IsEnemy(1,4) && TagTeam_IsEnemy(3,5) && !TagTeam_IsEnemy(4,5),724);
        Port_TagOptionSet(TAG_OPT_TAKEOVER,0);
    }
    if(tick==6) {
        /* The session behind this match (what the team setup page and the selector ask), then every change
           a player can make on that page, each one undone again. */
        static const s8 room[10]={0,0,2,-1,-1, 1,1,1,2,3};
        static const s8 holes[10]={0,-1,2,-1,-1, 1,1,1,2,3},same[10]={0,0,2,-1,-1, 0,1,1,2,3};
        Port_TagTestCheck(TagSession_Teams()==3 && TagSession_TeamSize(0)==2 && TagSession_TeamSize(2)==2 &&
            TagSession_TeamSize(3)==0 && TagSession_Size(0)==2 && TagSession_Size(1)==4 &&
            TagSession_MinSize(0)==2 && TagSession_MinSize(1)==4,732);
        Port_TagTestCheck(TagSession_SlotTeam(0,0)==0 && TagSession_SlotTeam(0,1)==0 && TagSession_SlotTeam(0,2)==-1 &&
            TagSession_SlotTeam(1,0)==1 && TagSession_SlotTeam(1,1)==1 && TagSession_SlotTeam(1,2)==2 &&
            TagSession_SlotTeam(1,3)==2 && TagSession_SlotTeam(1,4)==-1,733);
        Port_TagTestCheck(TagSession_PlayerTeam(0)==0 && TagSession_Owner(0,0)==0 && TagSession_Owner(0,1)==-1 &&
            TagSession_Owner(1,0)==-1,734);
        /* sizes: one to five, ten in the match */
        Port_TagTestCheck(TagSession_ChangeTeamSize(1,1) && TagSession_ChangeTeamSize(1,1) && TagSession_ChangeTeamSize(1,1) &&
            TagSession_TeamSize(1)==5 && !TagSession_ChangeTeamSize(1,1) && TagSession_SetTeamSize(2,3) &&
            !TagSession_SetTeamSize(2,4) && TagSession_Size(0)+TagSession_Size(1)==10,735);
        /* 2-5-3: teams 1 and 3 share row 0 (1 1 3 3 3 / 2 2 2 2 2) */
        Port_TagTestCheck(TagSession_Size(0)==5 && TagSession_SlotTeam(0,0)==0 && TagSession_SlotTeam(0,2)==2 &&
            TagSession_SlotTeam(0,4)==2 && TagSession_SlotTeam(1,0)==1 && TagSession_SlotTeam(1,4)==1,736);
        /* 4-4-2: no partition of whole teams, so team 3 stands on both rows (1 1 1 1 3 / 2 2 2 2 3), and a
           player who joins it gets its first slot */
        Port_TagTestCheck(TagSession_SetTeamSize(2,2) && TagSession_SetTeamSize(1,4) && TagSession_SetTeamSize(0,4) &&
            TagSession_Size(0)==5 && TagSession_Size(1)==5 && TagSession_SlotTeam(0,3)==0 && TagSession_SlotTeam(0,4)==2 &&
            TagSession_SlotTeam(1,3)==1 && TagSession_SlotTeam(1,4)==2,744);
        TagSession_SetPlayerTeam(0,2);
        Port_TagTestCheck(TagSession_Owner(0,4)==0 && TagSession_Owner(1,4)==-1 && TagSession_Owner(0,0)==-1,745);
        TagSession_SetPlayerTeam(0,0);
        Port_TagTestCheck(TagSession_SetTeamSize(0,2) && TagSession_SetTeamSize(1,2) && !TagSession_SetTeamSize(0,0) &&
            TagSession_ChangeTeamSize(0,-1) && TagSession_TeamSize(0)==1 && !TagSession_ChangeTeamSize(0,-1) &&
            TagSession_ChangeTeamSize(0,1) && TagSession_Size(0)==2 && TagSession_Size(1)==4,737);
        /* a player changes team: its seat is the first slot of that team; a team that does not exist is refused */
        TagSession_SetPlayerTeam(0,2);
        Port_TagTestCheck(TagSession_PlayerTeam(0)==2 && TagSession_Owner(1,2)==0 && TagSession_Owner(0,0)==-1,738);
        TagSession_SetPlayerTeam(0,3);
        Port_TagTestCheck(TagSession_PlayerTeam(0)==2,739);
        TagSession_SetPlayerTeam(0,0);
        Port_TagTestCheck(TagSession_PlayerTeam(0)==0 && TagSession_Owner(0,0)==0 && TagSession_Owner(1,2)==-1,740);
        /* the online room hands over a table; tables with a hole, or with one team opening both rows, are refused */
        Port_TagTestCheck(!TagSession_SetRoomTeams(4,holes) && TagSession_Teams()==2 &&
            !TagSession_SetRoomTeams(4,same) && !TagSession_SetRoomTeams(5,room) && !TagSession_SetRoomTeams(2,room),741);
        Port_TagTestCheck(TagSession_SetRoomTeams(4,room) && TagSession_Teams()==4 && TagSession_TeamSize(1)==3 &&
            TagSession_TeamSize(3)==1 && TagSession_Size(0)==3 && TagSession_Size(1)==5 &&
            TagSession_SlotTeam(0,2)==2 && TagSession_SlotTeam(1,4)==3 && TagSession_Owner(0,0)==-1,742);
        /* back to the three teams of two this match was started with */
        TagSession_SetTeams(3);
        Port_TagTestCheck(TagSession_Teams()==3 && TagSession_TeamSize(1)==2 && TagSession_Size(0)==2 &&
            TagSession_Size(1)==4 && TagSession_Owner(0,0)==0 && TagSession_SlotTeam(1,2)==2,743);
    }
    if(tick==30) {
        BtlMgrChr *c=BtlChar_Get(0);
        BtlMember_Damage(c,BtlMember_GetActiveGauge(c)->health+1000,0x1C3);
        BtlAct_ClearQueue(c);BtlAct_Request(c,0xD8);
    }
    if(tick==60) {
        Port_TagTestCheck(!TagTeam_IsAlive(0) && TagTeam_IsAlive(2) && TagTeam_Spectating(0),725);
        Port_TagTestCheck(TagTeam_TakeoverCandidate(0)<0,726);
        Port_TagTestCheck(TagTeam_ViewActor(0)==2,727);
        Port_TagTestCheck(!TagTeam_CheckEnd(0) && TagTeam_WinningTeam()==-1,728);
        Port_TagOptionSet(TAG_OPT_TAKEOVER,1);
    }
    /* The teammate is a CPU in a real fight: wait for a moment in which it can be taken over. */
    if(tick>=62 && !taken && TagTeam_TakeoverCandidate(0)==2 && TagTeam_Takeover(0)) {
        Port_TagTestCheck(TagTeam_ControlActor(0)==2 && TagTeam_Player(2)==0 && TagTeam_Player(0)<0,730);
        taken=tick;
    }
    if(tick==300) Port_TagTestCheck(taken,729);
    if(taken && tick==taken+8) {
        Port_TagTestCheck(TagTeam_ViewActor(0)==2 && !TagTeam_Spectating(0),731);
        Port_TagTestCheck(1,99);
    }
}

/* BT3_TAG_TEST_SQUAD=2..6: the team features in a match of three or more teams, with the fighters named by
   BT3_TAG_TEST_SQUAD_ACTORS. Every case runs once with its fighters on one roster row and once with the team
   that stands on both rows; the runner (port/tests/tag_squad_features_runtime.py) picks them and reads the notes. */
extern s32 Port_TagSquadActor(s32),Port_TagHitCount(s32,s32),Port_TagFusionResult(void);
extern void Port_TagTestNote(s32,s32,s32,s32,s32);
extern BtlMgrMember *BtlMember_GetActive(BtlMgrChr *);
extern s32 BtlParam_GetUnkB4(BtlMgrChr *,s32),BtlParam_GetUnkB1(BtlMgrChr *,s32);
extern s32 BtlAct_CanFuse(void *,s32,s32,s32,s32 *),BtlAct_QueueFusion(void *,s32,s32),BtlAct_GetQueued(BtlMgrChr *);
extern s32 BtlAct_GetTechniqueAction(BtlMgrChr *,s32),BtlCharApi_IsChanging(s32),BtlChar_TestFlag(BtlMgrChr *,s32);
extern s32 EftStruggle_IsActiveFor(s32),TagRevive_Helper(s32),TagRevive_Enabled(void),TagRevive_Duration(void),TagRevive_Cost(void);
extern f32 TagRevive_Radius(void),BtlCharApi_GetRadius(s32),atan2f(f32,f32);
extern void TagBeam_TestClashCount(s32,s32);

/* The cases direct single fighters; everybody else stands still: a fighter without a player reads an idle pad
   instead of the CPU's decisions, and only the fighters in the mask keep their stocks. */
static void squad_still(s32 stocks) {
    s32 i;
    for(i=0;i<TagTeam_Count();i++) {
        BtlMgrChr *c=BtlChar_Get(i);
        if(TagTeam_InputPlayer(i)<0) {
            c->injectOn=0;c->pad=3;
            TagTeam_Side(i)->control=BTL_CONTROL_PAD;TagTeam_Side(i)->pad=3;
        }
        if(!(stocks&(1<<i))) BtlMember_GetActiveGauge(c)->blast=0;
    }
}
static void squad_fell(s32 actor) {
    BtlMgrChr *c=BtlChar_Get(actor);
    BtlMember_Damage(c,BtlMember_GetActiveGauge(c)->health+1000,0x1C3);
    BtlAct_ClearQueue(c);BtlAct_Request(c,0xD8);
}
static s32 squad_aim(s32 actor,s32 target) {
    s32 n;
    for(n=0;n<TagTeam_Count() && TagTeam_Target(actor)!=target;n++) TagTeam_CycleTarget(actor);
    return TagTeam_Target(actor)==target;
}
/* 750: three or more teams, a and b on one team, e on another, the feature offered. The note tells the runner
   the roster rows of the three and the team. */
static void squad_open(s32 a,s32 b,s32 e,s32 feature) {
    s32 n=TagTeam_Count();
    Port_TagTestCheck(TagTeam_TeamCount()>=3 && (u32)a<(u32)n && (u32)b<(u32)n && (u32)e<(u32)n && a!=b &&
        !TagTeam_IsEnemy(a,b) && TagTeam_Team(a)==TagTeam_Team(b) && TagTeam_IsEnemy(a,e) && TagTeam_IsEnemy(b,e) &&
        TagTeam_Feature(feature),750);
    Port_TagTestNote(750,TagTeam_NativeSide(a),TagTeam_NativeSide(b),TagTeam_NativeSide(e),TagTeam_Team(a));
}

/* 2: revive. a = the rescuer, b = its teammate that falls, c = a fighter of another team. c stands beside the
   body with stocks for longer than a revival takes and nothing happens; then a comes and the revival runs. */
static void squad_revive(s32 tick) {
    static s32 came,done,stocks;
    s32 a=Port_TagSquadActor(0),b=Port_TagSquadActor(1),e=Port_TagSquadActor(2);
    BtlMgrChr *helper,*body,*other;
    BtlMgrGauge *g,*h;
    Vec4 p;
    if(tick<5) {squad_still(-1);return;}
    if(tick==5) {
        squad_open(a,b,e,TAG_FEATURE_REVIVE);
        Port_TagTestCheck(TagRevive_Enabled(),751);
    }
    helper=BtlChar_Get(a);body=BtlChar_Get(b);other=BtlChar_Get(e);
    g=BtlMember_GetActiveGauge(body);h=BtlMember_GetActiveGauge(helper);
    squad_still((tick>=75?1<<e:0)|(came?1<<a:0));
    if(tick==60) {squad_fell(b);Port_TagTestCheck(g->health==0,752);}
    if(tick==75) {
        p=((BtlMovePose *)&body->pose)->pos;p.x+=30;place(other,p);
        BtlMember_GetActiveGauge(other)->blast=BtlMember_GetActiveGauge(other)->blastMax;
    }
    if(tick==95 || tick==215) {
        Vec4 q=((BtlMovePose *)&other->pose)->pos;
        f32 x,y,z;
        p=((BtlMovePose *)&body->pose)->pos;x=q.x-p.x;y=q.y-p.y;z=q.z-p.z;
        /* in reach, alive, with the stocks a revival costs: and still nothing */
        Port_TagTestCheck(x*x+y*y+z*z<=TagRevive_Radius()*TagRevive_Radius() && TagTeam_IsAlive(e) &&
            BtlMember_GetActiveGauge(other)->blast>=TagRevive_Cost()*100000,753);
        Port_TagTestCheck(g->health==0 && TagRevive_Progress(b)==0 && TagRevive_Helper(b)==-1 &&
            TagRevive_Nearby(e)==-1,754);
    }
    if(tick==220) {
        p=((BtlMovePose *)&body->pose)->pos;p.x-=30;place(helper,p);
        h->blast=h->blastMax;came=tick;
    }
    if(tick==232) Port_TagTestCheck(TagRevive_Progress(b)>0 && TagRevive_Helper(b)==a && TagRevive_Nearby(a)==b,755);
    if(came && !done && g->health>0) {
        done=tick;
        Port_TagTestCheck(g->health==g->healthMax*Port_TagOption(TAG_OPT_REVIVE_HEALTH)/100 && TagTeam_IsAlive(b),756);
        Port_TagTestNote(757,tick-came,TagRevive_Duration(),stocks,h->blast);
        Port_TagTestCheck(stocks-h->blast>=TagRevive_Cost()*100000-5000 && stocks-h->blast<=TagRevive_Cost()*100000,757);
    }
    stocks=h->blast;
    if(done && tick==done+60) {
        Port_TagTestCheck(body->action!=0xD8 && body->action!=0xD9 && body->freeze==0 && TagTeam_IsAlive(b) &&
            TagRevive_Progress(b)==0,758);
        Port_TagTestCheck(1,99);
    }
    if(tick==600) Port_TagTestCheck(0,759);
}

/* 3: takeover and the fallen player's view. a = player 1's fighter, b = the teammate it takes over, c = another
   teammate that falls first (-1: none), so that the next living fighter by number after a is an enemy. At the
   end b falls too: with two other teams still fighting, no fighter is offered whatever the player looks at. */
static void squad_takeover(s32 tick) {
    static s32 taken,gone;
    s32 a=Port_TagSquadActor(0),b=Port_TagSquadActor(1),c=Port_TagSquadActor(2),i,n,next=-1;
    if(tick<5) {squad_still(-1);return;}
    if(tick==5) {
        squad_open(a,b,(a+1)%TagTeam_Count(),TAG_FEATURE_TAKEOVER);
        Port_TagTestCheck(TagTeam_ControlActor(0)==a && TagTeam_Player(a)==0 && TagTeam_Player(b)<0 &&
            TagTeam_ViewActor(0)==a && (c<0 || !TagTeam_IsEnemy(a,c)),761);
        Port_TagOptionSet(TAG_OPT_TAKEOVER,0);Port_TagOptionSet(TAG_OPT_REVIVE,0);
    }
    squad_still(0);
    if(tick==20 && c>=0) squad_fell(c);
    if(tick==30) squad_fell(a);
    if(tick==60) {
        for(n=1;n<TagTeam_Count() && next<0;n++) if(TagTeam_IsAlive((a+n)%TagTeam_Count())) next=(a+n)%TagTeam_Count();
        Port_TagTestCheck(next>=0 && next!=b && TagTeam_IsEnemy(a,next),762);
        Port_TagTestCheck(!TagTeam_IsAlive(a) && TagTeam_IsAlive(b) && TagTeam_Spectating(0) &&
            TagTeam_TakeoverCandidate(0)<0,763);
        Port_TagTestCheck(TagTeam_ViewActor(0)==b,764);
        Port_TagTestCheck(!TagTeam_CheckEnd(0) && TagTeam_WinningTeam()==-1,765);
        Port_TagOptionSet(TAG_OPT_TAKEOVER,1);
    }
    if(tick>=62 && !taken && TagTeam_TakeoverCandidate(0)==b && TagTeam_Takeover(0)) {
        Port_TagTestCheck(TagTeam_ControlActor(0)==b && TagTeam_Player(b)==0 && TagTeam_Player(a)<0,766);
        taken=tick;
    }
    if(tick==300) Port_TagTestCheck(taken,767);
    if(taken && tick==taken+8) Port_TagTestCheck(TagTeam_ViewActor(0)==b && !TagTeam_Spectating(0) &&
        TagTeam_InputPlayer(b)==0,768);
    if(taken && tick==taken+10) {squad_fell(b);gone=tick;}
    if(gone && tick==gone+40) {
        s32 offered=0,view=TagTeam_ViewActor(0);
        Port_TagTestCheck(!TagTeam_IsAlive(b) && TagTeam_Spectating(0) && !TagTeam_CheckEnd(0),769);
        Port_TagTestCheck(TagTeam_TakeoverCandidate(0)<0 && !TagTeam_Takeover(0),770);
        Port_TagTestCheck(TagTeam_IsAlive(view) && TagTeam_IsEnemy(b,view),771);
        for(i=0;i<TagTeam_Count();i++) {
            TagTeam_CycleSpectator(0);
            if(TagTeam_TakeoverCandidate(0)>=0 || TagTeam_Takeover(0)) offered++;
        }
        Port_TagTestCheck(!offered && TagTeam_ControlActor(0)==b,772);
        Port_TagTestCheck(1,99);
    }
}

/* The time over rule with a fused pair, asked as the battle sequence asks it when the clock runs out. First the
   fused body and one more fighter of every team lose health, so that no share is trivial (an enemy has fallen
   before). What the rule must add up for each team is noted; the runner compares it with the logged sums. */
static void squad_time_over(s32 fused,s32 pairMax,s32 fallen) {
    s32 hp[TAG_SQUAD_TEAMS]={0},full[TAG_SQUAD_TEAMS]={0},live[TAG_SQUAD_TEAMS]={0},cut[TAG_SQUAD_TEAMS]={0};
    s32 i,t,best=-1;
    for(i=0;i<TagTeam_Count();i++) {
        BtlMgrGauge *g=BtlMember_GetActiveGauge(BtlChar_Get(i));
        t=TagTeam_Team(i);
        if(TagFusion_Hidden(i) || !TagTeam_IsAlive(i)) continue;
        if(i==fused) g->health=g->healthMax/3;
        else if(i!=fallen && !cut[t]) {cut[t]=1;g->health-=1500*(t+2);}
    }
    for(i=0;i<TagTeam_Count();i++) {
        BtlMgrGauge *g=BtlMember_GetActiveGauge(BtlChar_Get(i));
        s32 health=TagTeam_IsAlive(i)?g->health:0,max=g->healthMax;
        t=TagTeam_Team(i);
        if(TagFusion_Hidden(i)) continue; /* (the partner is in the fused body) */
        if(i==fused) {health=(s32)((long long)health*pairMax/max);max=pairMax;}
        hp[t]+=health;full[t]+=max;live[t]+=TagTeam_IsAlive(i);
    }
    for(t=0;t<TagTeam_TeamCount();t++) {
        Port_TagTestNote(790+t,hp[t],full[t],live[t],0);
        if(live[t] && (best<0 || (long long)hp[t]*full[best]>(long long)hp[best]*full[t])) best=t;
    }
    Port_TagTestCheck(best>=0 && TagTeam_CheckEnd(1) && TagTeam_WinningTeam()==best,795);
}

/* 4: fusion. a and b = the pair (without players the partner agrees at once), c = a fighter of another team with
   b's character and a lower number than b, so that a search that forgot the teams would find it first.
   BT3_TAG_FUSION_RESULT names the fused character. A dance fusion separates after ten seconds; then b falls
   and a finds no partner although c still stands. A Potara fusion stays, and the time over rule is asked. */
static void squad_fusion(s32 tick) {
    static s32 slot=-1,dance,seen,back,maxA,maxB,charaA,charaB;
    s32 a=Port_TagSquadActor(0),b=Port_TagSquadActor(1),e=Port_TagSquadActor(2),i,k,partner=-1;
    BtlMgrChr *c,*p;
    BtlMgrMember *m;
    if(tick<5) {squad_still(-1);return;}
    if(tick==5) squad_open(a,b,e,TAG_FEATURE_FUSION);
    c=BtlChar_Get(a);p=BtlChar_Get(b);m=BtlMember_GetActive(c);
    squad_still((1<<a)|(1<<b));
    if(tick==20) {
        s32 queued;
        Port_TagOptionSet(TAG_OPT_FUSION_SECONDS,10);
        Port_TagOptionSet(TAG_OPT_SHARED_TRANSFORM,0);
        Port_TagOptionSet(TAG_OPT_REVIVE,0);
        charaA=m->chara;charaB=BtlMember_GetActive(p)->chara;
        maxA=BtlMember_GetActiveGauge(c)->healthMax;maxB=BtlMember_GetActiveGauge(p)->healthMax;
        BtlMember_GetActiveGauge(c)->blast=BtlMember_GetActiveGauge(c)->blastMax;
        BtlMember_GetActiveGauge(p)->blast=BtlMember_GetActiveGauge(p)->blastMax;
        for(i=0;i<3;i++) if(BtlParam_GetUnkB4(c,i)==Port_TagFusionResult()) slot=i;
        Port_TagTestCheck(slot>=0 && TagTeam_FusionsEnabled(),780);
        dance=BtlParam_GetUnkB1(c,slot)==1;
        Port_TagTestCheck(e<b && BtlMember_GetActive(BtlChar_Get(e))->chara==charaB && TagTeam_IsAlive(e),781);
        Port_TagTestCheck(BtlAct_CanFuse(c,slot,1,1,&partner) && partner==b,782);
        /* no fighter finds a partner on another team */
        for(i=0;i<TagTeam_Count();i++) for(k=0;k<3;k++) {
            s32 found=TagFusion_Find(i,k);
            if(found>=0 && TagTeam_IsEnemy(i,found)) Port_TagTestCheck(0,783);
        }
        Port_TagTestCheck(1,783);
        queued=BtlAct_QueueFusion(c,slot,partner);
        if(TagTeam_Player(b)<0) {
            Port_TagTestCheck(queued && TagFusion_Hidden(b),784);
            BtlAct_Request(c,BtlAct_GetQueued(c));
        } else {
            /* a player is asked first and answers with R3 */
            Port_TagTestCheck(!queued && !TagFusion_Hidden(b) && TagFusion_Requester(b)==a,784);
            gPad[TagTeam_Player(b)].pressed|=PAD_R3;
            TagFusion_Update();
            gPad[TagTeam_Player(b)].pressed&=~PAD_R3;
            Port_TagTestCheck(TagFusion_Hidden(b),796);
        }
    }
    if(tick>20 && m->chara==Port_TagFusionResult() && !BtlCharApi_IsChanging(c->objId) &&
       c->action!=0xF1 && c->action!=0xF2 && !seen) {
        seen=tick;
        Port_TagTestCheck(TagFusion_Hidden(b) && TagFusion_SharedBody(a)==a && TagFusion_Owner(b)==a,785);
        Port_TagTestCheck(m->gauge.healthMax==maxA+maxB && TagFusion_PairMax(a)==maxA+maxB,786);
        Port_TagTestCheck(TagTeam_IsAlive(a) && !TagTeam_IsAlive(b) && (TagFusion_Seconds(a)<0)==!dance,787);
        /* two players: both look at the fused fighter, in one view */
        if(TagTeam_Player(b)>=0) Port_TagTestCheck(TagTeam_ViewActor(TagTeam_Player(a))==a &&
            TagTeam_ViewActor(TagTeam_Player(b))==a && TagTeam_VisibleViews()==TagTeam_ViewCount()-1,797);
    }
    if(seen && !dance) {
        if(tick==seen+370) squad_fell(e);
        if(tick==seen+400) {
            Port_TagTestCheck(TagFusion_Seconds(a)==-1 && TagFusion_Hidden(b) && m->chara==Port_TagFusionResult() &&
                !TagTeam_IsAlive(e),788);
            squad_time_over(a,maxA+maxB,e);
            Port_TagTestCheck(1,99);
        }
    }
    if(seen && dance && !back && !TagFusion_Hidden(b)) {
        Vec4 pa=((BtlMovePose *)&c->pose)->pos,pb=((BtlMovePose *)&p->pose)->pos;
        f32 x=pa.x-pb.x,y=pa.y-pb.y,z=pa.z-pb.z,r=BtlCharApi_GetRadius(c->objId)+BtlCharApi_GetRadius(p->objId);
        back=tick;
        Port_TagTestNote(789,tick-seen,m->chara,BtlMember_GetActive(p)->chara,0);
        Port_TagTestCheck(m->chara==charaA && BtlMember_GetActive(p)->chara==charaB && TagFusion_SharedBody(a)<0 &&
            TagFusion_PairMax(a)==0,789);
        Port_TagTestCheck(m->gauge.healthMax==maxA && BtlMember_GetActiveGauge(p)->healthMax==maxB,790);
        Port_TagTestCheck(x*x+y*y+z*z>r*r,791);
        Port_TagTestCheck(tick-seen>=290,792);
    }
    if(back && tick==back+4) {
        Port_TagTestCheck(TagTeam_IsAlive(a) && TagTeam_IsAlive(b) && !BtlChar_TestFlag(p,0xB),793);
        if(TagTeam_Player(b)>=0) Port_TagTestCheck(TagTeam_ViewActor(TagTeam_Player(a))==a &&
            TagTeam_ViewActor(TagTeam_Player(b))==b && TagTeam_VisibleViews()==TagTeam_ViewCount() &&
            TagTeam_InputPlayer(a)==TagTeam_Player(a) && TagTeam_InputPlayer(b)==TagTeam_Player(b),798);
    }
    if(back && tick==back+10) squad_fell(b);
    if(back && tick==back+40) {
        Port_TagTestCheck(!TagTeam_IsAlive(b) && TagTeam_IsAlive(e) && TagFusion_Find(a,slot)<0,794);
        Port_TagTestCheck(1,99);
    }
    if(tick==1500) Port_TagTestCheck(0,799);
}

/* 5: beam assist. a = the fighter in the beam struggle, b = its teammate (helps on its own, as a CPU does),
   c = the enemy in the struggle, d = a fighter of a third team. d stands as near as b and has stocks: it must
   not help. Then it fires at a from the helper's side, so that the helper is the first body in the beam's way;
   what that does is noted (the two fighters of a struggle are protected by the game itself, with two teams as
   well). When the struggle is over, d fires at a again and that hit must count. */
static void squad_shot(s32 from,s32 at,f32 side) {
    BtlMgrChr *d=BtlChar_Get(from);
    Vec4 q=((BtlMovePose *)&BtlChar_Get(at)->pose)->pos,pos=q,rot={0,0,0,0};
    pos.x+=side;rot.y=atan2f(q.x-pos.x,q.z-pos.z);
    BtlChar_Place(d,&pos,&rot,BtlStage_FindZoneNear(-1,&pos));
    BtlMember_GetActiveGauge(d)->ki=BtlMember_GetActiveGauge(d)->kiMax;
    squad_aim(from,at);
    BtlAct_ClearQueue(d);BtlAct_Request(d,BtlAct_GetTechniqueAction(d,2));
}
static void squad_assist(s32 tick) {
    extern s32 BtlChar_IsFrozen(BtlMgrChr *);
    static s32 active,assisted,fired,ended,wrong,during,again,before,onHelper,onFighter;
    s32 who[4],i,n=TagTeam_Count();
    for(i=0;i<4;i++) who[i]=Port_TagSquadActor(i);
    if(tick<5) {squad_still(-1);return;}
    if(tick==5) {
        squad_open(who[0],who[1],who[2],TAG_FEATURE_ASSIST);
        Port_TagTestCheck((u32)who[3]<(u32)n && TagTeam_IsEnemy(who[3],who[0]) && TagTeam_IsEnemy(who[3],who[2]),800);
        Port_TagOptionSet(TAG_OPT_BEAM_ASSIST_CPU,1);
        Port_TagOptionSet(TAG_OPT_CINEMATIC_PAUSE,0);
        Port_TagOptionSet(TAG_OPT_REVIVE,0);
        Port_TagTestCheck(Port_TagOption(TAG_OPT_BEAM_ASSIST)==1 && Port_TagOption(TAG_OPT_SHARED_CLASH)==0,801);
    }
    squad_still((1<<who[0])|(1<<who[1])|(1<<who[2])|(1<<who[3]));
    if(tick==30) for(i=0;i<4;i++) {
        static const f32 xs[4]={0,35,0,-35},zs[4]={-150,-150,150,-150};
        BtlMgrChr *f=BtlChar_Get(who[i]);
        Vec4 pos={xs[i],-100.0f,zs[i],1},rot={0,i==2?3.14159265f:0,0,0};
        BtlAct_ClearQueue(f);BtlAct_Request(f,0xB);
        BtlMember_GetActiveGauge(f)->ki=BtlMember_GetActiveGauge(f)->kiMax;
        BtlMember_GetActiveGauge(f)->blast=300000;
        BtlChar_Place(f,&pos,&rot,BtlStage_FindZoneNear(-1,&pos));
    }
    if(tick>=30 && tick<=35) {squad_aim(who[0],who[2]);squad_aim(who[2],who[0]);}
    if(tick==35) {
        Port_TagTestCheck(TagTeam_Target(who[0])==who[2] && TagTeam_Target(who[2])==who[0],802);
        for(i=0;i<4;i+=2) BtlAct_Request(BtlChar_Get(who[i]),BtlAct_GetTechniqueAction(BtlChar_Get(who[i]),2));
    }
    /* only the teammate may ever help */
    for(i=0;i<n;i++) if(i!=who[1] && TagAssist_Active(i)) wrong++;
    if(EftStruggle_IsActiveFor(who[0])) {
        BtlMgrChr *d=BtlChar_Get(who[3]);
        active++;
        /* (an even struggle while the case looks at it, then a wins it) */
        if(active<=200) for(i=0;i<4;i+=2) TagBeam_TestClashCount(who[i],0);
        else TagBeam_TestClashCount(who[0],50);
        if(active==10) {
            Vec4 q=((BtlMovePose *)&BtlChar_Get(who[0])->pose)->pos,o=((BtlMovePose *)&d->pose)->pos;
            f32 x=o.x-q.x,z=o.z-q.z,reach=Port_TagOption(TAG_OPT_BEAM_ASSIST_RANGE);
            Port_TagTestCheck(BtlClash_Opponent(who[0])==who[2] && BtlClash_Opponent(who[2])==who[0] &&
                BtlClash_State(who[0])==2,803);
            /* as near and as ready as a helper must be */
            Port_TagTestCheck(x*x+z*z<=reach*reach && TagTeam_IsAlive(who[3]) && d->action>=0xB && d->action<0x37 &&
                BtlMember_GetActiveGauge(d)->blast>=100000,804);
            Port_TagTestCheck(TagAssist_ReadyAlly(who[3])==-1 && !TagAssist_Active(who[3]),805);
            Port_TagTestCheck(TagAssist_Ally(who[1])==who[0] || TagAssist_ReadyAlly(who[1])==who[0],806);
        }
        if(!assisted && TagAssist_Multiplier(who[0])>100) {
            assisted=tick;
            Port_TagTestCheck(TagAssist_Multiplier(who[0])==Port_TagOption(TAG_OPT_BEAM_ASSIST_POWER) &&
                TagAssist_Ally(who[1])==who[0],807);
        }
        if(assisted && tick==assisted+5) {
            squad_shot(who[3],who[0],120.0f);
            Port_TagTestCheck(TagTeam_Target(who[3])==who[0],808);
            fired=tick;
        }
        if(fired && tick==fired+45) Port_TagTestNote(813,BtlChar_TestFlag(BtlChar_Get(who[0]),0xAA),
            BtlChar_IsFrozen(BtlChar_Get(who[0])),BtlChar_TestFlag(BtlChar_Get(who[1]),0xAA),BtlChar_IsFrozen(BtlChar_Get(who[1])));
        if(fired && tick==fired+90) Port_TagTestNote(814,Port_TagHitCount(who[3],who[1]),Port_TagHitCount(who[3],who[0]),
            TagAssist_Active(who[1]),TagAssist_Multiplier(who[0]));
        onHelper=Port_TagHitCount(who[3],who[1]);onFighter=Port_TagHitCount(who[3],who[0]);
        if((onHelper || onFighter) && !during) during=tick;
    } else if(active && BtlClash_Opponent(who[0])<0) ended++;
    if(ended==45 && !again) {
        squad_shot(who[3],who[0],-120.0f);
        before=BtlMember_GetActiveGauge(BtlChar_Get(who[0]))->health;
        again=tick;
    }
    if(again && tick>again && (Port_TagHitCount(who[3],who[0])>onFighter || tick==again+200)) {
        Port_TagTestNote(809,active,assisted,fired,during);
        Port_TagTestNote(810,onHelper,onFighter,Port_TagHitCount(who[3],who[0])-onFighter,
            before-BtlMember_GetActiveGauge(BtlChar_Get(who[0]))->health);
        Port_TagTestCheck(active>10 && assisted && fired && !wrong,809);
        /* the third team's beam reached the helper while the struggle ran */
        Port_TagTestCheck(onHelper>0 && during,813);
        Port_TagTestCheck(Port_TagHitCount(who[3],who[0])>onFighter &&
            BtlMember_GetActiveGauge(BtlChar_Get(who[0]))->health<before,810);
        Port_TagTestCheck(!TagAssist_Active(who[1]) && TagAssist_Multiplier(who[0])==100 &&
            Port_TagHitCount(who[1],who[0])==0 && Port_TagHitCount(who[0],who[1])==0,811);
        Port_TagTestCheck(1,99);
    }
    if(tick==1200) {
        Port_TagTestNote(812,active,assisted,fired,ended);
        Port_TagTestCheck(0,812);
    }
}

/* 6: Outnumbered (the Balanced preset, CPU fighters included). Fighters fall in two steps: actors a and b at
   the first, c and d at the second (-1: nobody). Before the first step and after each one a marker is noted,
   and for every living fighter what 1000 points of its damage become on its first living enemy. The numbers
   the help uses are in the tagbalance lines; the runner knows the teams and says what they must be. */
static void squad_outnumbered(s32 tick) {
    s32 i,j,step;
    if(tick<5) {squad_still(-1);return;}
    if(tick==5) {
        Port_TagTestCheck(TagTeam_TeamCount()>=3 && TagTeam_Feature(TAG_FEATURE_OUTNUMBERED),820);
        Port_TagOptionSet(TAG_OPT_OUTNUMBERED,1);Port_TagOptionSet(TAG_OPT_OUT_HUMANS,0);
        Port_TagOptionSet(TAG_OPT_OUT_SCOPE,0);Port_TagOptionSet(TAG_OPT_REVIVE,0);
    }
    squad_still(0);
    for(step=0;step<2;step++) if(tick==100+100*step) for(i=0;i<2;i++)
        if(Port_TagSquadActor(step*2+i)>=0) squad_fell(Port_TagSquadActor(step*2+i));
    for(step=0;step<3;step++) if(tick==90+100*step) {
        Port_TagTestNote(830,step,0,0,0);
        for(i=0;i<TagTeam_Count();i++) if(TagTeam_IsAlive(i)) for(j=0;j<TagTeam_Count();j++)
            if(TagTeam_IsEnemy(i,j) && TagTeam_IsAlive(j)) {
                Port_TagTestNote(831,i,j,TagBalance_Modify(j,i,1000,0),step);
                break;
            }
        if(step==2) Port_TagTestCheck(1,99);
    }
}

void TagTeam_TestTick(void) {
    static s32 tick, beforeMove, beforeBlock;
    BtlMgrChr *rescuer,*body;
    BtlMgrGauge *r,*g;
    BtlMovePose *rp,*bp;
    /* Online fixtures own their clock and completion state across rematches. */
    {extern s32 TagNet_Enabled(void);if(TagNet_Enabled())return;}
    {extern s32 Port_TagModeRushTest(void);extern void TagModeRush_TestTick(void);
     if(Port_TagModeRushTest()) {TagModeRush_TestTick();return;}}
    /* Ring-out coverage follows the actual finish and victory states too. */
    if(Port_TagControlsTest()==4) {
        static s32 ringTick;
        if(TagTeam_Active() && (BtlSeq_IsFighting() || ringTick)) TagControls_TestTick(++ringTick);
        return;
    }
    if((!Port_TagReviveTest()&&!Port_TagAudioTest()&&!Port_TagClashTest()&&!Port_TagControlsTest()&&!Port_TagBeamTest()&&!Port_TagCameraTest()&&!Port_TagFusionTest()&&!Port_TagGiantTest()&&!Port_TagCpuTest()&&!Port_TagStageTest()&&!Port_TagCinemaTest()&&!Port_TagResultTest()&&!Port_TagSquadTest()) || !TagTeam_Active() || !BtlSeq_IsFighting()) return;
    if(Battle_GetWork()->flags & BATTLE_FLAG_PAUSE) return;
    tick++;
    { extern s32 Port_TagShowcase(void);
      if(Port_TagShowcase()) {TagBeam_TestTick(tick);return;} }
    if(Port_TagCinemaTest()) {TagCinema_MatrixTick(tick);return;}
    if(Port_TagSquadTest()) {
        switch(Port_TagSquadTest()) {
        case 2: squad_revive(tick);break;
        case 3: squad_takeover(tick);break;
        case 4: squad_fusion(tick);break;
        case 5: squad_assist(tick);break;
        case 6: squad_outnumbered(tick);break;
        default: squad_test(tick);
        }
        return;
    }
    if(Port_TagResultTest()) {
        if(tick==90) {
            s32 i,lose=Port_TagResultTest()==2?0:1;
            /* Three or more teams: the value is the winning team (1..5) and everybody else falls. */
            for(i=0;i<TagTeam_Count();i++) if(TagTeam_TeamCount()>=3?TagTeam_Team(i)!=Port_TagResultTest()-1:TagTeam_Team(i)==lose) {
                BtlMgrChr *c=BtlChar_Get(i);
                BtlMember_Damage(c,BtlMember_GetActiveGauge(c)->health+1000,0x1C3);
                BtlAct_ClearQueue(c);BtlAct_Request(c,0xD8);
            }
        }
        if(tick>180 && TagTeam_IsAlive(0)&&TagTeam_IsAlive(1)&&TagTeam_IsAlive(2)&&TagTeam_IsAlive(3)) {
            extern void Port_TagMenuTrace(s32,s32,s32,s32,s32,s32);
            Port_TagMenuTrace(92,TagTeam_Count(),TagTeam_ViewCount(),TagTeam_Team(0),TagTeam_Team(1),TagTeam_TeamCount()>=3?TagTeam_TeamCount():0);
        }
        return;
    }
    if(Port_TagStageTest()) {TagStage_TestTick(tick);return;}
    if(Port_TagCpuTest()) {TagCpu_TestTick(tick);return;}
    /* The catcher fixture places its actors below the arena itself; ordinary
       spawn spacing has separate coverage and is not its starting condition. */
    if(tick==1 && !Port_TagAudioTest() && Port_TagControlsTest()!=5)check_start_spacing();
    if(Port_TagGiantTest()) { TagGiant_TestTick(tick); return; }
    if(Port_TagCameraTest()) { TagCamera_TestTick(tick); return; }
    if(Port_TagFusionTest()) { TagFusion_TestTick(tick); return; }
    if(Port_TagBeamTest()) { TagBeam_TestTick(tick); return; }
    if(Port_TagControlsTest()) { TagControls_TestTick(tick); return; }
    if(Port_TagClashTest()) { TagClash_TestTick(tick); return; }
    if(Port_TagAudioTest()) { if(tick==30) audio_check(); return; }
    rescuer=BtlChar_Get(0); body=BtlChar_Get(2);
    r=BtlMember_GetActiveGauge(rescuer); g=BtlMember_GetActiveGauge(body);
    rp=(BtlMovePose *)&rescuer->pose; bp=(BtlMovePose *)&body->pose;
    if(tick==60) {
        Vec4 p=rp->pos; p.y=0; place(rescuer,p);
        p.x+=30; place(body,p);
        r->blast=400000;
        BtlMember_Damage(body,g->health+1000,0x1C3);
        Port_TagTestCheck(g->health==0,10);
        BtlAct_ClearQueue(body); BtlAct_Request(body,0xD8);
    }
    if(tick==65) {
        /* Exercise the real target/camera path while the revival meter fills. */
        s32 tries;
        for(tries=0;tries<TagTeam_Count() && TagTeam_Target(0)!=2;tries++)
            TagTeam_CycleTarget(0);
        Port_TagTestCheck(TagTeam_Target(0)==2,16);
    }
    if(tick==80) {
        extern void Port_TagTestState(s32,s32,s32,s32);
        extern void Port_TagTestPositions(u32,u32);
        Port_TagTestState(body->action,g->health,r->blast,TagRevive_Progress(2));
        Port_TagTestPositions((u32)rp,(u32)bp);
        Vec4 p=bp->pos;
        Port_TagTestCheck(TagRevive_Progress(2)>0,1);
        Port_TagTestCheck(TagRevive_Nearby(0)==2,17);
        p.x-=100; place(rescuer,p);
    }
    if(tick==82) {
        extern void Port_TagTestPositions(u32,u32);
        extern void Port_TagTestState(s32,s32,s32,s32);
        Port_TagTestPositions((u32)rp,(u32)bp);
        Port_TagTestState(body->action,g->health,r->blast,TagRevive_Progress(2));
        Port_TagTestCheck(TagRevive_Progress(2)==0,2);
        Port_TagTestCheck(TagRevive_Nearby(0)==-1,18);
    }
    if(tick==100) { Vec4 p=bp->pos; p.x-=30; place(rescuer,p); }
    if(tick==110) {
        Vec4 p=rp->pos; p.z+=5; beforeMove=TagRevive_Progress(2); place(rescuer,p);
    }
    if(tick==111) Port_TagTestCheck(TagRevive_Progress(2)>beforeMove,11);
    if(tick==120) BtlAct_Request(rescuer,0x38);
    if(tick==121) {
        Port_TagTestCheck(BtlColl_IsGuarding(rescuer),12);
        beforeBlock=TagRevive_Progress(2);
        BtlMember_Damage(rescuer,100,0x1C3);
    }
    if(tick==122) Port_TagTestCheck(TagRevive_Progress(2)>beforeBlock,13);
    if(tick==135) {
        Port_TagTestCheck(TagRevive_Progress(2)>0,3);
        Port_TagTestCheck(!BtlColl_IsGuarding(rescuer),14);
        BtlMember_Damage(rescuer,1000,0x1C3);
    }
    if(tick==136) Port_TagTestCheck(TagRevive_Progress(2)==0,4);
    if(tick==230) {
        Port_TagTestCheck(g->health==g->healthMax/4,5);
        Port_TagTestCheck(r->blast>=200000 && r->blast<300000,6);
        Port_TagTestCheck(body->action!=0xD8 && body->action!=0xD9 && body->freeze==0,7);
        Port_TagTestCheck(TagTeam_IsEnemy(0,TagTeam_Target(0)),17);
    }
    if(tick==320) Port_TagTestCheck(body->action==0xB,15);
    if(tick==350) { g->health=0; BtlChar_SetHeldFlag(body,7); }
    if(tick==460) { Port_TagTestCheck(g->health==0 && TagRevive_Progress(2)==0,8); Port_TagTestCheck(1,99); }
}
#endif
