#ifndef MENU_TAG_SETUP_H
#define MENU_TAG_SETUP_H
#include "types.h"
void TagSetup_Reset(void);
void TagSetup_Draw(void);
/* 1: continue to fighter selection, -1: back, 0: still choosing. */
s32 TagSetup_Input(void);
/* A team's colour (0..4: blue, red, green, gold, violet), lightened towards 1 or darkened towards -1. */
u32 TagSetup_TeamColor(s32 team,f32 light,s32 alpha);
#endif
