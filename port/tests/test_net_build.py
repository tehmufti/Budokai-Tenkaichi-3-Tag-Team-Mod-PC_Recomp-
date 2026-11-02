"""Build identities match across packaging, not across changed code or stale objects."""
import pathlib, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import net_build

class BuildIdentity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.temp.name)
        self.source=self.root/'src/battle/test.c';self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'int simulation(void) { return 1; }\n')
        self.obj=self.root/'objects';self.obj.mkdir()
        self.data=self.root/'tables';self.data.mkdir()
        (self.obj/'test.o').write_bytes(b'compiled game')
        (self.data/'SKELETON').write_text('skeleton')
        self.family=patch.object(net_build,'compiler_family',return_value='x64-softfloat:22.1.0:')
        self.family.start()
    def tearDown(self):
        self.family.stop();self.temp.cleanup()
    def record(self):
        net_build.save_manifest(self.root,self.obj,self.data,'win64',net_build.source_digest(self.root))
    def identity(self,variant='win64'):
        return net_build.checked_identity(self.root,self.obj,self.data,variant)
    def test_windows_linux_share_same_source_identity(self):
        self.record();self.assertEqual(self.identity(),self.identity('clang64'))
    def test_line_endings_and_unrelated_files_are_not_versions(self):
        self.record();before=self.identity()
        self.source.write_bytes(self.source.read_bytes().replace(b'\n',b'\r\n'))
        (self.root/'notes.txt').write_text('private local note')
        self.assertEqual(before,self.identity())
    def test_changed_code_requires_recompile_and_changes_identity(self):
        self.record();before=self.identity()
        self.source.write_text('int simulation(void) { return 2; }\n')
        with self.assertRaises(SystemExit):self.identity()
        self.record();self.assertNotEqual(before,self.identity())
    def test_changed_object_requires_recompile(self):
        self.record();(self.obj/'test.o').write_bytes(b'other build')
        with self.assertRaises(SystemExit):self.identity()
    def test_no_completed_compile_cannot_link(self):
        with self.assertRaises(SystemExit):self.identity()
    def test_changed_source_during_compile_cannot_be_recorded(self):
        started=net_build.source_digest(self.root)
        self.source.write_text('int simulation(void) { return 3; }\n')
        with self.assertRaises(SystemExit):net_build.save_manifest(self.root,self.obj,self.data,'win64',started)
    def test_compiler_family_changes_reject_old_record(self):
        self.record()
        with patch.object(net_build,'compiler_family',return_value='another-architecture'):
            with self.assertRaises(SystemExit):self.identity()

if __name__=='__main__':unittest.main()
