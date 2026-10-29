"""Upgrade preservation and interrupted-update recovery using real files."""
from pathlib import Path
import hashlib,json,os,struct,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'port/tools'))
import native_update as updater
import native_setup as setup


class UpdateTests(unittest.TestCase):
    def fixture(self,root,platform='windows',version='beta.1'):
        target=root/'installed game';payload=root/'update files/payload'
        target.mkdir();payload.mkdir(parents=True)
        exe='engine/TagTeam.exe' if platform=='windows' else 'engine/TagTeam'
        names=[exe,exe+'.mem','engine/TagTeam.dat',
               'engine/SDL3.dll' if platform=='windows' else 'engine/lib/libSDL3.so.0','release.json']
        if platform=='windows':names.append('Play.exe')
        old={};new={}
        for name in names:
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b'old '+name.encode());old[name]=updater.digest(dest)
            dest=payload/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b'new '+name.encode());new[name]=updater.digest(dest)
        (payload/'engine/TagTeam.dat').write_bytes(b'TTMD'+struct.pack('<IQ',0,0xcbf29ce484222325))
        (payload/'release.json').write_text(json.dumps({'version':'beta.3','platform':platform+'-x86_64'}))
        for name in names:new[name]=updater.digest(payload/name)
        (payload/'manifest.json').write_text(json.dumps(new))
        (target/'installation.json').write_text(json.dumps({'schema':1,'platform':platform,'profile':'bt3-us','language':'es','version':version,'files':old}))
        keep={
            'settings.txt':b'menu_lang="es"\nkey_p1_cross=27\ntag_target_button=2\n',
            'saves/card1/BASLUS-21678DBZT3/BASLUS-21678DBZT3':bytes(range(256))*64,
            'saves/native-bt4-custom.bin':b'custom equipment',
            'saves/unrelated.txt':b'player note',
            'gamedata/pzs3us2/00001.bin':b'disc resource',
            'gamedata/native-tables0.bin':b'tables zero',
            'gamedata/native-tables1.bin':b'tables one',
            'screenshots/keep.png':b'user screenshot',
        }
        for name,data in keep.items():
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        return target,payload,keep

    def unchanged(self,target,keep):
        for name,data in keep.items():self.assertEqual((target/name).read_bytes(),data,name)

    def test_saves_settings_assets_preserved_for_old_same_and_higher_versions(self):
        for platform in ('windows','linux'):
            for version in ('beta.1','beta.2','beta.3','beta.46'):
                with self.subTest(platform=platform,version=version),tempfile.TemporaryDirectory() as folder:
                    target,payload,keep=self.fixture(Path(folder),platform,version)
                    with patch.object(setup,'platform_name',return_value=platform):updater.update(target,payload,progress=lambda _:None)
                    self.unchanged(target,keep)
                    state=json.loads((target/'installation.json').read_text())
                    self.assertEqual(state['version'],'beta.3');self.assertEqual(state['language'],'es')
                    self.assertTrue(state['build']);self.assertFalse((target/'.tag-team-update').exists())
                    for name,digest in state['files'].items():self.assertEqual(updater.digest(target/name),digest)
                    if platform=='linux':self.assertEqual((target/'Play.sh').read_text(),setup.PLAY_LINUX)
                    # Repair changed program files even when the version matches.
                    (target/'engine/TagTeam.dat').write_bytes(b'old replacement')
                    with patch.object(setup,'platform_name',return_value=platform):updater.update(target,payload,progress=lambda _:None)
                    self.assertEqual((target/'engine/TagTeam.dat').read_bytes(),(payload/'engine/TagTeam.dat').read_bytes())
                    self.unchanged(target,keep)

    def test_failure_restores_original_program_and_saves(self):
        with tempfile.TemporaryDirectory() as folder:
            target,payload,keep=self.fixture(Path(folder));before={p.relative_to(target).as_posix():p.read_bytes() for p in target.rglob('*') if p.is_file()}
            replace=os.replace;failed=False
            def fail_once(src,dest):
                nonlocal failed
                if Path(dest)==target/'engine/TagTeam.dat' and not failed:failed=True;raise OSError('simulated disk error')
                return replace(src,dest)
            with patch.object(setup,'platform_name',return_value='windows'),patch.object(updater.os,'replace',side_effect=fail_once):
                with self.assertRaisesRegex(OSError,'simulated'):updater.update(target,payload,progress=lambda _:None)
            self.unchanged(target,before);self.assertFalse((target/'.tag-team-update').exists())

    def test_interrupted_update_recovers_before_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            target,payload,keep=self.fixture(Path(folder));work=target/'.tag-team-update'
            backup=work/'old/engine/TagTeam.exe';backup.parent.mkdir(parents=True);backup.write_bytes((target/'engine/TagTeam.exe').read_bytes())
            (target/'engine/TagTeam.exe').write_bytes(b'partial update')
            (work/'journal.json').write_text(json.dumps({'complete':False,'files':{'engine/TagTeam.exe':updater.digest(backup)}}))
            with patch.object(setup,'platform_name',return_value='windows'):updater.update(target,payload,progress=lambda _:None)
            self.unchanged(target,keep);self.assertEqual((target/'engine/TagTeam.exe').read_bytes(),(payload/'engine/TagTeam.exe').read_bytes())

    def test_corrupt_update_or_wrong_platform_does_not_replace_game(self):
        for corrupt in (True,False):
            with tempfile.TemporaryDirectory() as folder:
                target,payload,keep=self.fixture(Path(folder));before=(target/'engine/TagTeam.exe').read_bytes()
                if corrupt:(payload/'engine/TagTeam.exe').write_bytes(b'damaged')
                with patch.object(setup,'platform_name',return_value='windows' if corrupt else 'linux'):
                    with self.assertRaises(ValueError):updater.update(target,payload,progress=lambda _:None)
                self.unchanged(target,keep);self.assertEqual((target/'engine/TagTeam.exe').read_bytes(),before)

    def test_save_and_traversal_paths_rejected_even_in_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('saves/card1/save','settings.txt','../save','engine/../../save','C:/save','engine\\save','/engine/save','engine/./save','gamedata/pzs3us0/000.bin'):
                with self.subTest(name=name),self.assertRaises(ValueError):updater.safe_path(root,name,True)

    def test_missing_tables_requires_matching_disc_without_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            target,payload,keep=self.fixture(Path(folder))
            with patch.object(updater.native_tables,'verify',side_effect=ValueError('new ranges')),patch.object(setup,'platform_name',return_value='windows'):
                with self.assertRaisesRegex(ValueError,'same disc'):updater.update(target,payload,progress=lambda _:None)
                self.unchanged(target,keep)
                with patch.object(updater.native_tables,'identify',return_value=({'id':'bt4-es'},[],[])):
                    with self.assertRaisesRegex(ValueError,'same game'):updater.update(target,payload,iso='wrong.iso',progress=lambda _:None)
                self.unchanged(target,keep)

    def test_unknown_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            target,payload,keep=self.fixture(Path(folder));path=target/'installation.json';state=json.loads(path.read_text());del state['files']['Play.exe'];path.write_text(json.dumps(state))
            original=(target/'Play.exe').read_bytes()
            with patch.object(setup,'platform_name',return_value='windows'),self.assertRaisesRegex(ValueError,'not owned'):
                updater.update(target,payload,progress=lambda _:None)
            self.assertEqual((target/'Play.exe').read_bytes(),original);self.unchanged(target,keep)


if __name__=='__main__':unittest.main()
