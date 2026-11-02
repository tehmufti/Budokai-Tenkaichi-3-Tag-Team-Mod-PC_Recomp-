/* Actual asynchronous catalogue hashing with tiny synthetic resource volumes. */
#include <SDL3/SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
static const char *root;
static int calls,cancel;
const char *Port_FileRoot(void){return root;}
int PortGame_IsBT4(void){return 1;}
int PortGame_VolumeCount(int part){return part>=0 && part<4?2:0;}
int Port_DataFingerprint(unsigned long long *out){*out=1;return 1;}
int TagNet_DataProgress(unsigned done,unsigned total){calls++;if(done>total)abort();return cancel;}
extern unsigned long long TagNet_DataIdentity(void);
extern int TagNet_DataCancelled(void);
int main(int argc,char **argv) {
    char path[1600];FILE *f;unsigned char data[65536];unsigned long long a,b;
    if(argc!=2)return 2;root=argv[1];SDL_Init(0);
    for(int p=0;p<4;p++) {
        snprintf(path,sizeof(path),"%s/pzs4us%d",root,p);SDL_CreateDirectory(path);
        for(int i=0;i<2;i++) {
            snprintf(path,sizeof(path),"%s/pzs4us%d/%05d.bin",root,p,i);
            f=fopen(path,"wb");if(!f)return 3;memset(data,17*p+i,sizeof(data));
            for(int j=0;j<8;j++)fwrite(data,1,sizeof(data),f);fclose(f);
        }
    }
    a=TagNet_DataIdentity();if(!a || !calls || TagNet_DataCancelled())return 4;
    b=TagNet_DataIdentity();if(a!=b)return 5;
    cancel=1;if(TagNet_DataIdentity() || !TagNet_DataCancelled())return 6;
    cancel=0;if(TagNet_DataIdentity()!=a || TagNet_DataCancelled())return 7;
    /* Size changes invalidate cached identity on filesystems with coarse times. */
    snprintf(path,sizeof(path),"%s/pzs4us2/00001.bin",root);
    f=fopen(path,"ab");fputc(1,f);fclose(f);
    b=TagNet_DataIdentity();if(!b || b==a)return 8;
    remove(path);if(TagNet_DataIdentity()!=0 || TagNet_DataCancelled())return 9;
    printf("PASS: progress, cached content, cancellation, retry, changed and missing files\n");
    SDL_Quit();return 0;
}
