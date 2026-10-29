"""Exercise the real persistent settings store in two separate processes."""
from pathlib import Path
import os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
SOURCE=r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
extern int Port_Setting(const char *,int);
extern void Port_SettingSave(const char *,int),Port_SettingsWrite(void);
extern void Port_SettingTextSave(const char *,const char *);
extern void Port_SettingText(const char *,const char *,char *,int);
int main(int argc,char **argv) {
    int i;char key[64],text[64];
    if(argc>1 && !strcmp(argv[1],"write")) {
        for(i=0;i<500;i++){sprintf(key,"keyboard_and_mod_setting_%03d",i);Port_SettingSave(key,i+1);}
        Port_SettingTextSave("menu_lang","es");Port_SettingsWrite();return 0;
    }
    for(i=0;i<500;i++){sprintf(key,"keyboard_and_mod_setting_%03d",i);if(Port_Setting(key,-1)!=i+1)return 1;}
    Port_SettingText("menu_lang","en",text,sizeof(text));if(strcmp(text,"es"))return 2;
    Port_SettingSave("tag_practice_recovery_text",0);Port_SettingsWrite();
    return 0;
}
'''

def main():
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);c=root/'check.c';c.write_text(SOURCE);exe=root/'check'
        subprocess.run([os.environ.get('CC','cc'),str(c),str(ROOT/'port/src/plat_settings.c'),'-pthread','-o',str(exe)],check=True)
        env={**os.environ,'BT3_SETTINGS':str(root/'settings.txt')}
        subprocess.run([str(exe),'write'],env=env,check=True)
        subprocess.run([str(exe),'read'],env=env,check=True)
        text=(root/'settings.txt').read_text()
        assert 'tag_practice_recovery_text=0' in text
        assert len([l for l in text.splitlines() if l.startswith('keyboard_and_mod_setting_')])==500
    print('PASS 500 bindings/options, long names, language, save and reload')

if __name__=='__main__':main()
