"""Update an installed Recomp game without replacing saves, settings or disc assets."""
import argparse
from contextlib import contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import queue
import shutil
import sys
import threading

import native_setup as setup
import native_tables

ROOT_FILES = {'Play.exe', 'Play.sh', 'Read me.txt', 'Tag Team Mod Logo.png',
              'a11y_es.txt', 'release.json', 'installation.json'}
ROOT_DIRS = {'engine', 'fonts', 'licenses', 'translations', 'tbo', 'lang'}
TABLES = {'gamedata/native-tables0.bin', 'gamedata/native-tables1.bin'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(stream.read()).hexdigest()


def safe_path(root, name, tables=False):
    """Only program-owned files. Save paths are never accepted, even in a journal."""
    parts = PurePosixPath(name).parts
    if not parts or '\\' in name or ':' in name or name.startswith('/') or any(p in ('.', '..') for p in parts) or '/'.join(parts) != name:
        raise ValueError('Invalid update path')
    if not (name in ROOT_FILES or (len(parts)>1 and parts[0] in ROOT_DIRS) or (tables and name in TABLES)):
        raise ValueError('Update tried to replace a file outside the program: '+name)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink() or (current.exists() and getattr(current.stat(), 'st_file_attributes', 0)&0x400):
            raise ValueError('Linked files cannot be replaced by the updater: '+name)
    if root.resolve() not in current.resolve().parents:
        raise ValueError('Update path escaped the installation')
    return current


def atomic_json(path, value):
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)


@contextmanager
def update_lock(target):
    path=target/'.tag-team-update.lock'
    if path.is_symlink():raise ValueError('Invalid update lock')
    with path.open('a+b') as stream:
        stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError('Another update is already running.') from error
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream,fcntl.LOCK_UN)


def ensure_closed(target, platform):
    exe=safe_path(target,'engine/TagTeam.exe' if platform=='windows' else 'engine/TagTeam')
    if os.name=='nt':
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
        kernel.CreateFileW.restype=ctypes.c_void_p
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.CreateFileW(str(exe),0xC0000000,0,None,3,0,None)
        if handle==ctypes.c_void_p(-1).value:
            raise ValueError('Close the game before updating. The program file is in use or not writable.')
        kernel.CloseHandle(handle)
    elif Path('/proc').is_dir():
        for entry in Path('/proc').glob('[0-9]*/exe'):
            try:
                if entry.resolve()==exe.resolve():raise ValueError('Close the game before updating.')
            except (OSError,RuntimeError):pass


def remove_work(target,work):
    # This fixed folder is created exclusively by this updater, after checking
    # that no previous folder exists. Never clean an unknown or linked tree.
    if work.parent.resolve()!=target.resolve() or work.name!='.tag-team-update' or work.is_symlink():
        raise ValueError('Invalid update workspace')
    for p in work.rglob('*'):
        if p.is_symlink():raise ValueError('Unexpected link in update workspace')
    shutil.rmtree(work)


def recover(target, work):
    if not work.exists():return
    journal=work/'journal.json'
    if work.is_symlink() or not journal.is_file():
        raise ValueError('Unrecognized .tag-team-update folder. Keep it and choose your installed game folder.')
    state=json.loads(journal.read_text(encoding='utf-8'))
    if not state.get('complete'):
        for name,old in reversed(list(state['files'].items())):
            dest=safe_path(target,name,tables=True)
            if old is None:
                dest.unlink(missing_ok=True)
            else:
                backup=safe_path(work/'old',name,tables=True)
                if not backup.is_file() or digest(backup)!=old:
                    raise ValueError('An interrupted update backup is damaged. Keep .tag-team-update for recovery.')
                # Copy instead of moving: recovery can itself be interrupted.
                dest.parent.mkdir(parents=True,exist_ok=True)
                temp=work/'restore.tmp';shutil.copy2(backup,temp);os.replace(temp,dest)
    remove_work(target,work)


def tables_for_update(target, payload, state, iso=None):
    dat=(payload/'engine/TagTeam.dat').read_bytes()
    try:
        tables=[safe_path(target,f'gamedata/native-tables{i}.bin',True).read_bytes() for i in range(2)]
        native_tables.verify(tables,dat)
        return {} # Existing startup tables already cover the new executable.
    except (OSError,ValueError):pass
    if iso is None:
        raise ValueError('This update needs additional startup tables. Select the same disc image (.iso) used to install this game. Saves and imported assets will stay in place.')
    profile,blobs,sizes=native_tables.identify(iso)
    if profile['id']!=state['profile']:
        raise ValueError('Choose the same game, region and disc revision as this installation.')
    tables=native_tables.reconstruct(profile,blobs,sizes)
    native_tables.verify(tables,dat)
    return {f'gamedata/native-tables{i}.bin':bytes(data) for i,data in enumerate(tables)}


def update(target, payload=setup.PAYLOAD, iso=None, progress=print):
    target,payload=Path(target).resolve(),Path(payload).resolve()
    if target==payload or target in payload.parents or payload in target.parents:
        raise ValueError('Extract the updater outside your installed game folder.')
    metadata=safe_path(target,'installation.json')
    if not metadata.is_file():raise ValueError('Choose the existing Recomp installation folder containing Play and installation.json.')
    work=target/'.tag-team-update'
    with update_lock(target):
        state=json.loads(metadata.read_text(encoding='utf-8'))
        platform=setup.platform_name()
        if state.get('platform')!=platform:raise ValueError('Download the updater for this installation\'s operating system.')
        ensure_closed(target,platform)
        recover(target,work)
        state=json.loads(metadata.read_text(encoding='utf-8'))
        if state.get('schema')!=1 or not isinstance(state.get('files'),dict):raise ValueError('Unsupported installation record.')
        progress('Checking update / Comprobando actualización...')
        files=setup.payload_files(payload)
        release=json.loads((payload/'release.json').read_text(encoding='utf-8'))
        if release.get('platform')!=platform+'-x86_64':raise ValueError('Wrong updater platform.')
        for name in files:
            dest=safe_path(target,name)
            if dest.exists() and name not in state['files'] and name not in {'Play.sh'}:
                raise ValueError('A file not owned by the installer would be replaced: '+name)
        extra=tables_for_update(target,payload,state,iso)
        if platform=='linux':extra['Play.sh']=setup.PLAY_LINUX.encode('utf-8')
        needed=sum((payload/n).stat().st_size for n in files)*2+sum(map(len,extra.values()))*2+16*1024*1024
        if shutil.disk_usage(target).free<needed:raise ValueError('Not enough free space to safely stage and back up this update.')
        work.mkdir()
        (work/'new').mkdir();(work/'old').mkdir()
        journal={'complete':False,'files':{}}
        atomic_json(work/'journal.json',journal)
        try:
            for name,expected in files.items():
                staged=safe_path(work/'new',name);staged.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(payload/name,staged)
                if digest(staged)!=expected:raise ValueError('Update copy failed its integrity check: '+name)
            for name,data in extra.items():
                staged=safe_path(work/'new',name,True);staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(data)
            record={**state,'files':files,'version':release.get('version'),
                    'build':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}
            atomic_json(work/'new/installation.json',record)
            names=list(dict.fromkeys([*files,*extra,'installation.json']))
            if platform=='linux':
                for name in ('Play.sh','engine/TagTeam'):(work/'new'/name).chmod(0o755)
            progress('Updating program files / Actualizando el programa...')
            for name in names:
                dest=safe_path(target,name,True)
                if dest.exists():
                    backup=safe_path(work/'old',name,True);backup.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(dest,backup);journal['files'][name]=digest(backup)
                else:journal['files'][name]=None
                # Persist recovery before each replacement, including newly added files.
                atomic_json(work/'journal.json',journal)
                dest.parent.mkdir(parents=True,exist_ok=True)
                os.replace(work/'new'/name,dest)
            journal['complete']=True;atomic_json(work/'journal.json',journal)
        except BaseException:
            recover(target,work)
            raise
        remove_work(target,work)
    progress('Updated. Your saves and settings were kept. / Actualizado. Se han conservado tus partidas y ajustes.')
    return target


def gui():
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    win=tk.Tk();win.title('Tag Team Mod — Update / Actualizar');win.geometry('740x340');win.minsize(620,340)
    frame=ttk.Frame(win,padding=20);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1)
    ttk.Label(frame,text='Update your Recomp installation',font=('Segoe UI',18,'bold')).grid(row=0,column=0,columnspan=3,sticky='w')
    ttk.Label(frame,text='Choose your existing game folder. Saves, settings and imported disc data are kept.\nElige la carpeta del juego instalado. Se conservan las partidas, los ajustes y el disco importado.',wraplength=670).grid(row=1,column=0,columnspan=3,sticky='w',pady=12)
    destination=tk.StringVar();disc=tk.StringVar();events=queue.Queue();busy=False
    def browse(var,iso=False):
        value=filedialog.askopenfilename(filetypes=[('Disc image (.iso)','*.iso')]) if iso else filedialog.askdirectory()
        if value:var.set(value)
    entries=[]
    for row,title,var in [(2,'Game folder / Carpeta del juego',destination),(3,'Disc (.iso), only if requested',disc)]:
        ttk.Label(frame,text=title).grid(row=row,column=0,sticky='w',padx=(0,10),pady=6)
        entry=ttk.Entry(frame,textvariable=var);entry.grid(row=row,column=1,sticky='ew');entries.append(entry)
        button=ttk.Button(frame,text='Browse / Examinar',command=lambda v=var,i=row==3:browse(v,i));button.grid(row=row,column=2,padx=(8,0));entries.append(button)
    status=ttk.Label(frame,text='',wraplength=670);status.grid(row=5,column=0,columnspan=3,sticky='w',pady=10)
    bar=ttk.Progressbar(frame,mode='determinate',value=0);bar.grid(row=6,column=0,columnspan=3,sticky='ew')
    def begin():
        nonlocal busy
        if busy:return
        if not destination.get():messagebox.showerror('Update','Choose the installed game folder. / Elige la carpeta del juego.');return
        busy=True
        for widget in [*entries,start]:widget.configure(state='disabled')
        bar.configure(mode='indeterminate');bar.start()
        def worker():
            try:update(destination.get(),iso=disc.get() or None,progress=lambda text:events.put(('status',text)));events.put(('done',None))
            except Exception as error:events.put(('error',str(error)))
        threading.Thread(target=worker,daemon=True).start()
    def poll():
        nonlocal busy
        while not events.empty():
            kind,value=events.get()
            if kind=='status':status.configure(text=value)
            else:
                busy=False;bar.stop();bar.configure(mode='determinate',value=100 if kind=='done' else 0)
                for widget in [*entries,start]:widget.configure(state='normal')
                if kind=='error':messagebox.showerror('Update / Actualizar',value)
        win.after(100,poll)
    start=ttk.Button(frame,text='Update / Actualizar',command=begin);start.grid(row=4,column=2,sticky='e',pady=12)
    def close():
        if busy:messagebox.showinfo('Update','Please wait for the update to finish. / Espera a que termine la actualización.')
        else:win.destroy()
    win.protocol('WM_DELETE_WINDOW',close);win.after(100,poll);win.mainloop()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path);parser.add_argument('--payload',type=Path,default=setup.PAYLOAD)
    parser.add_argument('--iso',type=Path)
    args=parser.parse_args()
    if args.destination:update(args.destination,args.payload,args.iso)
    else:gui()
