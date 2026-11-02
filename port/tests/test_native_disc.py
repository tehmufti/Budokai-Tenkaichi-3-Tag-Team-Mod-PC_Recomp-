"""PS2 imports use ISO9660, including discs with stale optional UDF metadata."""
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import pycdlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_disc import GameDisc


class DiscTests(unittest.TestCase):
    def make_disc(self,path):
        disc=pycdlib.PyCdlib();disc.new(udf='2.60')
        payload=b'PS2 game data'*300
        disc.add_fp(io.BytesIO(payload),len(payload),iso_path='/GAME.BIN;1',udf_path='/GAME.BIN')
        disc.write(str(path));disc.close()
        return payload

    def test_stale_udf_end_does_not_block_iso9660(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'disc.iso';payload=self.make_disc(path)
            with path.open('r+b') as f:
                f.seek(16*2048+80);f.write(struct.pack('<I',10000)+struct.pack('>I',10000))
            broken=pycdlib.PyCdlib()
            with self.assertRaises(struct.error):broken.open(str(path))
            disc=GameDisc();disc.open(path)
            try:
                with disc.open_file_from_iso(iso_path='/GAME.BIN;1') as f:
                    self.assertEqual(f.read(),payload)
            finally:disc.close()

    def test_truncated_game_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'disc.iso';self.make_disc(path)
            disc=GameDisc();disc.open(path)
            record=disc.get_record(iso_path='/GAME.BIN;1')
            end=record.extent_location()*2048+record.data_length;disc.close()
            with path.open('r+b') as f:f.truncate(end-20)
            with self.assertRaisesRegex(ValueError,'incomplete'):
                GameDisc().open(path)

    def test_read_only(self):
        with self.assertRaisesRegex(ValueError,'read-only'):GameDisc().open('disc.iso','r+b')

if __name__=='__main__':unittest.main()
