#ifndef BATTLE_TAG_CONTROLS_H
#define BATTLE_TAG_CONTROLS_H
#include "tag_options.h"
/* PS2 logical buttons: keyboard and gamepad bindings feed the same actions. */
static inline unsigned TagControl_Button(int value) { return 1u << (value & 15); }
static inline const char *TagControl_Name(int value) {
    static const char *names[]={"Select","L3","R3","Start","Up","Right","Down","Left",
        "L2","R2","L1","R1","Triangle","Circle","Cross","Square"};
    return names[value & 15];
}
static inline int TagControl_MenuButton(int value) {
    static const int buttons[]={0,1,2,3,8,9,10,11,15};
    return buttons[value>=0 && value<9?value:0];
}
static inline int TagControl_Ticks(int centiseconds) {
    int n=(centiseconds*30+99)/100; return n>0?n:1;
}
/* Negative means consumed until release. Tap mode waits for release so a
   shared target/lock-off button cannot perform both actions on one hold. */
static inline int TagControl_Press(int *state,int held,int ticks,int onRelease) {
    if(!held) { int fire=onRelease && *state>=ticks; *state=0; return fire; }
    if(*state<0)return 0;
    if(*state<30001)++*state;
    if(!onRelease && *state>=ticks) { *state=-1;return 1; }
    return 0;
}
#endif
