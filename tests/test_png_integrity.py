"""Offline static-PNG integrity checks; no image or system writes."""
from __future__ import annotations

import struct
from pathlib import Path
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from png_integrity import PngIntegrityError, inspect_png_integrity  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402

SIG = b"\x89PNG\r\n\x1a\n"


def chunk(kind, body=b""):
    packet = kind + body
    return struct.pack(">I", len(body)) + packet + struct.pack(">I", zlib.crc32(packet))


def make_png(data, *, width=1, height=1, kind=b"IDAT"):
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return SIG + chunk(b"IHDR", ihdr) + chunk(kind, data) + chunk(b"IEND")


class StaticPNGIntegrityTests(unittest.TestCase):
    def test_normal_png_and_split_idat(self):
        original = solid_png((4, 5, 6))
        self.assertEqual(inspect_png_integrity(original), (32, 32))
        ihdr_end = 8 + 25
        idat_len = struct.unpack_from(">I", original, ihdr_end)[0]
        payload = original[ihdr_end + 8:ihdr_end + 8 + idat_len]
        split = (original[:ihdr_end] + chunk(b"IDAT", payload[:7])
                 + chunk(b"IDAT", payload[7:]) + chunk(b"IEND"))
        self.assertEqual(inspect_png_integrity(split), (32, 32))

    def test_malformed_crc_and_ihdr_geometry(self):
        bad = bytearray(solid_png((1, 2, 3)))
        bad[-6] ^= 2
        with self.assertRaisesRegex(PngIntegrityError, "crc"):
            inspect_png_integrity(bytes(bad))
        with self.assertRaisesRegex(PngIntegrityError, "geometry"):
            inspect_png_integrity(make_png(zlib.compress(b"\x00\x01\x02\x03"), width=8192, height=8192))

    def test_compressed_bomb_bound_by_expected_scanline_length(self):
        bomb = make_png(zlib.compress(b"\x00" * (4 * 1024 * 1024)))
        with self.assertRaisesRegex(PngIntegrityError, "inflate_limit"):
            inspect_png_integrity(bomb)

    def test_valid_crc_but_invalid_deflate_and_missing_end(self):
        with self.assertRaisesRegex(PngIntegrityError, "invalid_png_deflate"):
            inspect_png_integrity(make_png(b"not-zlib"))
        good = solid_png((9, 8, 7))
        with self.assertRaisesRegex(PngIntegrityError, "missing_png_end"):
            inspect_png_integrity(good[:-12])
        with self.assertRaisesRegex(PngIntegrityError, "invalid_png_end"):
            inspect_png_integrity(good + b"forged trailing payload")

    def test_forged_iend_in_idat_and_noncontiguous_idat(self):
        fake = make_png(zlib.compress(b"\x00\x01\x02\x03") + b"IEND")
        with self.assertRaises(PngIntegrityError):
            inspect_png_integrity(fake)
        body = zlib.compress(b"\x00\x01\x02\x03")
        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        split = (SIG + ihdr + chunk(b"IDAT", body[:5]) + chunk(b"tEXt", b"abc")
                 + chunk(b"IDAT", body[5:]) + chunk(b"IEND"))
        with self.assertRaisesRegex(PngIntegrityError, "noncontiguous_png_idat"):
            inspect_png_integrity(split)

    def test_unknown_critical_and_bad_filter_and_extra_raw_bytes(self):
        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        compressed = zlib.compress(b"\x00\x01\x02\x03")
        unknown = SIG + ihdr + chunk(b"ZZZZ") + chunk(b"IDAT", compressed) + chunk(b"IEND")
        with self.assertRaisesRegex(PngIntegrityError, "unsupported_critical"):
            inspect_png_integrity(unknown)
        with self.assertRaisesRegex(PngIntegrityError, "scanline_filter"):
            inspect_png_integrity(make_png(zlib.compress(b"\x05\x01\x02\x03")))
        with self.assertRaisesRegex(PngIntegrityError, "inflate_limit"):
            inspect_png_integrity(make_png(zlib.compress(b"\x00\x01\x02\x03\x04")))

    def test_ancillary_png_chunk_with_valid_crc_is_allowed(self):
        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        sample = SIG + ihdr + chunk(b"tEXt", b"Note\x00valid") + chunk(b"IDAT", zlib.compress(b"\x00\x01\x02\x03")) + chunk(b"IEND")
        self.assertEqual(inspect_png_integrity(sample), (1, 1))


if __name__ == "__main__":
    unittest.main()
