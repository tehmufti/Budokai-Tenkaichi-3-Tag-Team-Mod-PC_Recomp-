"""Platform-neutral room identity, tied to the sources actually compiled.

An executable hash differs between PE and ELF even for identical game code.
Hash the shared source/build rules instead; game-data hashes and per-frame
simulation digests still check disc compatibility and determinism separately.
"""
import hashlib, json, os, pathlib, re, subprocess

SOURCE_DIRS = ('src', 'include', 'port/src', 'port/include', 'port/data',
               'port/third_party/newlib_libm', 'port/third_party/xxhash')
SOURCE_EXTS = {'.c', '.h', '.cpp', '.inc', '.inl', '.s'}
BUILD_TOOLS = ('net_build.py', 'undefined.py', 'link.py', 'toolchain.py',
               'portsrc.py', 'eeconst.py', 'ptr32.py', 'irfix.py', 'macwin.py')

def source_digest(root):
    root = pathlib.Path(root)
    paths = {p for directory in SOURCE_DIRS for p in (root / directory).rglob('*')
             if p.is_file() and p.suffix.lower() in SOURCE_EXTS}
    paths.update(root / 'port/tools' / name for name in BUILD_TOOLS
                 if (root / 'port/tools' / name).is_file())
    h = hashlib.sha256(b'TagTeam shared source v1\0')
    for p in sorted(paths, key=lambda p: p.relative_to(root).as_posix()):
        name = p.relative_to(root).as_posix().encode()
        data = p.read_bytes().replace(b'\r\n', b'\n')
        h.update(len(name).to_bytes(4, 'big')); h.update(name)
        h.update(len(data).to_bytes(8, 'big')); h.update(data)
    return h.hexdigest()

def compiler_family(variant):
    # Only the tested x86-64 soft-float builds share a family. ARM and legacy
    # 32-bit builds retain their own identity until they are exercised too.
    family = 'x64-softfloat' if variant in ('win64', 'clang64') else variant
    cc = 'clang' if variant != 'gcc' else 'gcc'
    version = subprocess.check_output([cc, '--version'], text=True).splitlines()[0]
    version = re.search(r'(\d+\.\d+\.\d+)', version).group(1)
    return family + ':' + version + ':' + os.environ.get('BT3_PORT_CFLAGS', '').strip()

def objects_digest(directories):
    h = hashlib.sha256()
    for index, directory in enumerate(directories):
        for p in sorted(pathlib.Path(directory).glob('*.o')):
            h.update(str(index).encode() + b'/' + p.name.encode() + b'\0')
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

def save_manifest(root, obj, data, variant, started):
    current = source_digest(root)
    if current != started:
        raise SystemExit('Sources changed during compilation. Rebuild before linking.')
    family = compiler_family(variant)
    # Disc-derived static tables must not be confused with a skeleton build.
    embedded = pathlib.Path(root) / 'port/build/gen/data'
    tables = 'skeleton'
    if not (pathlib.Path(data) / 'SKELETON').exists():
        h = hashlib.sha256()
        for p in sorted(embedded.glob('*.s')):
            h.update(p.name.encode()+b'\0'+p.read_bytes().replace(b'\r\n',b'\n'))
        tables = h.hexdigest()
    identity = hashlib.sha256((current+'\n'+family+'\n'+tables).encode()).hexdigest()
    record = dict(source=current, family=family, identity=identity,
                  objects=objects_digest((obj, data)))
    (pathlib.Path(obj) / 'tag-net-build.json').write_text(json.dumps(record, indent=2)+'\n')

def checked_identity(root, obj, data, variant):
    path = pathlib.Path(obj) / 'tag-net-build.json'
    if not path.exists():
        raise SystemExit('No completed build record. Run port/tools/undefined.py first.')
    record = json.loads(path.read_text())
    if (record['source'] != source_digest(root) or
        record['family'] != compiler_family(variant) or
        record['objects'] != objects_digest((obj, data))):
        raise SystemExit('Sources or objects changed since compilation. Run port/tools/undefined.py again.')
    return int(record['identity'][:16], 16)
