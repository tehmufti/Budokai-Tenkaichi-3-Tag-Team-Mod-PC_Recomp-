#ifndef TAG_NET_H
#define TAG_NET_H
#include "../../../include/battle/tag_options.h"
#include "../../../include/battle/tag_lobby_rules.h"
#ifdef __cplusplus
extern "C" {
#endif
enum { TN_FIGHTERS=10, TN_PLAYERS=10, TN_SPECTATORS=10, TN_OBSERVER=10, TN_OPTIONS=TAG_OPT_COUNT };
typedef struct TagNetConfig {
    int revision,disc,seed,stage,music,time,cpu,size[2];
    int chara[10],costume[10],owner[10],options[TN_OPTIONS];
    int cpuLevel[10],items[10][8];
    /* Persistent-room identity is separate from a claimed battle slot. */
    int party,practice,mode,preset,heal,speed;
    TlRoom lobby;
} TagNetConfig;
static inline void TagNet_CopyFighter(TagNetConfig *c,int to,int from) {
    int j;c->chara[to]=c->chara[from];c->costume[to]=c->costume[from];c->owner[to]=c->owner[from];c->cpuLevel[to]=c->cpuLevel[from];
    for(j=0;j<8;j++)c->items[to][j]=c->items[from][j];
    c->lobby.draft.team[to]=c->lobby.draft.team[from];
}
/* A lobby's Team Battle with three to five teams: every setup slot carries its team (lobby.draft.team). */
static inline int TagNet_TeamRoom(const TagNetConfig *c) {
    return c->party && !c->practice && c->mode==TL_TEAM && c->lobby.draft.teams>=3;
}
/* Puts the fighters of such a room where the layout rule wants their teams (TlTeams_Arrange) and sets both
   row sizes. Returns the new slot of fighter `follow`, or -1 with the room untouched when a team would be
   empty or hold more than five. The room page and the host share it. */
static inline int TagNet_ArrangeTeams(TagNetConfig *c,int follow) {
    TagNetConfig old=*c;int rows[2],order[10],k,n=c->size[0]+c->size[1],to=-1;
    if(!TlTeams_Arrange(c->lobby.draft.teams,n,old.lobby.draft.team,rows,order))return -1;
    for(k=0;k<n;k++) {
        int j,from=order[k];
        c->chara[k]=old.chara[from];c->costume[k]=old.costume[from];c->owner[k]=old.owner[from];c->cpuLevel[k]=old.cpuLevel[from];
        for(j=0;j<8;j++)c->items[k][j]=old.items[from][j];
        c->lobby.draft.team[k]=old.lobby.draft.team[from];
        if(from==follow)to=k;
    }
    c->size[0]=rows[0];c->size[1]=rows[1];
    return to<0?0:to;
}
typedef struct TagNetStatus {
    int phase,role,host,connected,playerMask,ready[TN_PLAYERS],spectators,view,freeCam;
    unsigned frame,rollbacks;
    char message[192];
    TagNetConfig config;
} TagNetStatus;
/* The network and local camera are deliberately outside the rollback state.
 * Only agreed inputs and the immutable match configuration enter the game. */
int TagNet_Enabled(void);
void TagNet_Enable(int enabled);
void TagNet_Party(int enabled);
int TagNet_IsParty(void);
int TagNet_IsPractice(void);
int TagNet_Observer(void);
void TagNet_ChooseMode(int mode);
void TagNet_ChoosePreset(int mode,int preset);
/* The host's mode menu: Team Battle with this many teams (2..5). */
void TagNet_ChooseTeams(int teams);
int TagNet_HostMenu(void);
int TagNet_HostPoll(void);
int TagNet_HostChoosing(void);
typedef struct TagLobbyRoster {int count,role,host,waiting;int member[10],ping[10];char code[8];} TagLobbyRoster;
void TagNet_Roster(unsigned address);
void TagLobbyRoster_Draw(int hostMenu);
void TagNet_ReturnPractice(void);
int TagNet_PracticeEnding(void);
typedef struct TagPracticeUi {int visible,host,choice,role;TlRoom lobby;} TagPracticeUi;
typedef struct TagPracticeEvent {unsigned at;int member,present,generation,kind;TlLoadout fighter;} TagPracticeEvent;
void TagNet_PracticeUi(unsigned address);
void TagNet_PracticeState(unsigned address);
void TagNet_PracticeScores(unsigned address);
int TagNet_PracticeEvent(unsigned index,unsigned address);
int TagNet_MemberPresent(int member);
void TagNet_Kick(int member);
void TagNet_Tournament(unsigned address);
void TagNet_SkipTournament(void);
void TagNet_BattleResult(int winningSide);
/* The match had this many teams (2 unless three to five fought) and this team won (-1: a draw). */
void TagNet_BattleTeams(int teams,int winningTeam);
/* Opt-in fixture (BT3_TAG_TEST_TEAM_DIFFER): the setup slot whose team this copy alone changes, or -1. */
int TagNet_TestTeamDiffer(void);
void TagNet_PracticeLoadout(int member,unsigned address);
int TagNet_NativeMenu(void);
int TagNet_Active(void);
int TagNet_Role(void);
int TagNet_MenuInput(void);
int TagNet_Resim(void);
int TagNet_Stopped(void);
int TagNet_Room(void);
void TagNet_MenuPoll(void);
void TagNet_CopyConfig(unsigned address);
void TagNet_Loaded(void);
void TagNet_Finished(void);
void TagNet_Tick(unsigned blank);
void TagNet_Input(int player,unsigned char *data);
void TagNet_Status(TagNetStatus *out);
void TagNet_Start(int role,const char *address,int port);
void TagNet_Edit(const TagNetConfig *config);
void TagNet_Ready(int ready);
/* Lobby only: release your fighter or claim an available one (-1 = automatic). */
void TagNet_SwitchRole(int playing,int fighter);
void TagNet_Leave(void);
void TagNet_Watch(int actor,int freeCam);
int TagNet_View(void);
int TagNet_FreeCamera(float *position,float *rotation);
int TagNet_Option(int id,int fallback);
int TagNet_SpeedMilli(void);
void TagNet_Draw(void);
#ifdef __cplusplus
}
#endif
#endif
