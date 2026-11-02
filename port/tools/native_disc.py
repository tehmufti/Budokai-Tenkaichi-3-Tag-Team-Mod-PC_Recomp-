"""Read the ISO9660 filesystem used by the PS2, without the optional UDF tree.

Some otherwise usable disc images retain UDF anchors pointing beyond the end
of the image. The game does not use those anchors. All imports address files
by ISO9660 name and still verify executable hashes and resource bounds.
"""
import struct
import pycdlib


class GameDisc(pycdlib.PyCdlib):
    def _parse_volume_descriptors(self):
        super()._parse_volume_descriptors()
        # Confine this compatibility override to our read-only disc importer.
        # Do not attempt the unused, possibly stale UDF directory tree.
        self._has_udf = False
        # pycdlib silently shortens files whose declared extent is past EOF.
        # Check the raw ISO9660 records before that recovery can hide a bad dump.
        self._cdfp.seek(0, 2)
        size = self._cdfp.tell()
        root = self.pvd.root_directory_record()
        pending = [(root.extent_location(), root.data_length)]
        visited = set()
        while pending:
            extent, length = pending.pop()
            if (extent, length) in visited:
                continue
            visited.add((extent, length))
            if length > 16 * 1024 * 1024 or extent * self.logical_block_size + length > size:
                raise ValueError('The disc image is incomplete: an ISO9660 directory is missing.')
            self._cdfp.seek(extent * self.logical_block_size)
            data = self._cdfp.read(length)
            offset = 0
            while offset < len(data):
                record_length = data[offset]
                if not record_length:
                    offset = (offset // self.logical_block_size + 1) * self.logical_block_size
                    continue
                if record_length < 34 or offset + record_length > len(data):
                    raise ValueError('The disc image has a damaged ISO9660 directory.')
                start = struct.unpack_from('<I', data, offset + 2)[0]
                count = struct.unpack_from('<I', data, offset + 10)[0]
                if count and start * self.logical_block_size + count > size:
                    raise ValueError('The disc image is incomplete: a game file extends beyond the end of the .iso. Copy or dump the complete disc again.')
                if data[offset + 25] & 2:
                    pending.append((start, count))
                offset += record_length

    def open(self, filename, mode='rb'):
        if mode != 'rb':
            raise ValueError('Game discs are read-only.')
        try:
            super().open(str(filename), mode)
        except struct.error as error:
            if self._initialized:
                self.close()
            raise ValueError('The disc image has a missing or damaged ISO9660 directory. Copy or dump the complete .iso again.') from error
        except Exception:
            if self._initialized:
                self.close()
            raise
