"""Apply the pinned PE32 host-free compatibility patch to a private DLL copy."""

import hashlib
import struct


def patch_null_host_free(original, destination):
    """Match the 0281 client's cuMemFreeHost(NULL) behaviour in the pinned PE32 bridge."""
    data = bytearray(original.read_bytes())
    if hashlib.sha256(data).hexdigest() != (
            'c3da2f9b2d3e8e0141e946ae254a5eead96574a17f2570da1534160670ff3ac1'):
        raise ValueError('Unexpected PE32 CUDA bridge')
    pe, = struct.unpack_from('<I', data, 0x3c)
    header_size, = struct.unpack_from('<H', data, pe + 20)
    text = pe + 24 + header_size
    if data[pe:pe + 4] != b'PE\0\0' or data[text:text + 8] != b'.text\0\0\0':
        raise ValueError('Expected the pinned PE32 text section')
    used, text_rva, raw_size, raw = struct.unpack_from('<IIII', data, text + 8)
    entry_rva = 0x35ea0
    entry = raw + entry_rva - text_rva
    prologue = bytes.fromhex('55 89 e5 53 57 56')
    if data[entry:entry + len(prologue)] != prologue:
        raise ValueError('Unexpected cuMemFreeHost prologue')

    # stdcall PE32. NULL returns success and pops one argument. Other pointers
    # execute the original prologue, then continue into the original routine.
    cave = raw + used
    cave_rva = text_rva + used
    thunk = bytes.fromhex('83 7c 24 04 00 75 05 31 c0 c2 04 00') + prologue
    thunk += b'\xe9' + struct.pack('<i', entry_rva + len(prologue) - (cave_rva + len(thunk) + 5))
    if used + len(thunk) > raw_size or any(data[cave:cave + len(thunk)]):
        raise ValueError('Expected unused raw padding at the end of .text')
    data[cave:cave + len(thunk)] = thunk
    struct.pack_into('<I', data, text + 8, used + len(thunk))
    data[entry:entry + len(prologue)] = b'\xe9' + struct.pack('<i', cave_rva - (entry_rva + 5)) + b'\x90'
    destination.write_bytes(data)
