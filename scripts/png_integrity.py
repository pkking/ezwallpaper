#!/usr/bin/env python3
"""Bounded PNG structure + DEFLATE scanline check for greeter *preflight*.

Supports only 8-bit noninterlaced RGB/RGBA PNGs. This is NOT a trusted
privileged image decoder, and does not produce pixels or sanitize a file.
"""
from __future__ import annotations

import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 64 * 1024 * 1024
MAX_EDGE = 8192
MAX_PIXELS = 16_000_000


class PngIntegrityError(Exception):
    """Opaque parser refusal. Never echo untrusted PNG bytes."""


def inspect_png_integrity(blob: bytes) -> tuple[int, int]:
    if len(blob) > MAX_PNG_BYTES or len(blob) < 57 or blob[:8] != PNG_SIGNATURE:
        raise PngIntegrityError("invalid_png_signature_or_size")
    pos = 8
    width = height = channels = 0
    header_seen = palette_seen = idat_seen = idat_done = False
    inflated = bytearray()
    inflater = zlib.decompressobj()
    expected = 0
    while pos < len(blob):
        if len(blob) - pos < 12:
            raise PngIntegrityError("truncated_png_chunk")
        length = struct.unpack_from(">I", blob, pos)[0]
        start = pos + 8
        end = start + length
        if end + 4 > len(blob):
            raise PngIntegrityError("truncated_png_chunk")
        kind = blob[pos + 4:pos + 8]
        if (len(kind) != 4 or any(not (65 <= x <= 90 or 97 <= x <= 122) for x in kind)
                or not (65 <= kind[2] <= 90)):
            raise PngIntegrityError("invalid_png_chunk_type")
        payload = memoryview(blob)[start:end]
        crc = struct.unpack_from(">I", blob, end)[0]
        if zlib.crc32(payload, zlib.crc32(kind)) & 0xffffffff != crc:
            raise PngIntegrityError("png_chunk_crc_mismatch")
        pos = end + 4
        if not header_seen:
            if kind != b"IHDR" or length != 13:
                raise PngIntegrityError("missing_png_ihdr")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if (not 1 <= width <= MAX_EDGE or not 1 <= height <= MAX_EDGE
                    or width * height > MAX_PIXELS or depth != 8
                    or color not in (2, 6) or compression or filtering or interlace):
                raise PngIntegrityError("unsupported_png_geometry")
            channels = 3 if color == 2 else 4
            expected = height * (width * channels + 1)
            header_seen = True
            continue
        if kind == b"IHDR":
            raise PngIntegrityError("duplicate_png_ihdr")
        if kind == b"IDAT":
            if idat_done:
                raise PngIntegrityError("noncontiguous_png_idat")
            idat_seen = True
            # A decompression bomb cannot exceed the bounded expected raw
            # scanlines; max_length prevents allocating an unbounded buffer.
            remaining = expected - len(inflated)
            if remaining < 0:
                raise PngIntegrityError("png_inflate_limit")
            try:
                decoded = inflater.decompress(payload, remaining + 1)
            except zlib.error as exc:
                raise PngIntegrityError("invalid_png_deflate") from exc
            inflated.extend(decoded)
            if len(inflated) > expected or inflater.unconsumed_tail or inflater.unused_data:
                raise PngIntegrityError("png_inflate_limit")
            continue
        if idat_seen:
            idat_done = True
        if kind == b"PLTE":
            if palette_seen or idat_seen or channels != 3 or length == 0 or length > 768 or length % 3:
                raise PngIntegrityError("invalid_png_palette")
            palette_seen = True
        elif kind == b"IEND":
            if not idat_seen or length != 0 or pos != len(blob) or not inflater.eof:
                raise PngIntegrityError("invalid_png_end")
            # All image scanlines must have been inflated, not just the header.
            if len(inflated) != expected:
                raise PngIntegrityError("incomplete_png_scanlines")
            stride = width * channels + 1
            for index in range(height):
                if inflated[index * stride] > 4:
                    raise PngIntegrityError("invalid_png_scanline_filter")
            return width, height
        elif not (kind[0] & 0x20):
            raise PngIntegrityError("unsupported_critical_png_chunk")
    raise PngIntegrityError("missing_png_end")
