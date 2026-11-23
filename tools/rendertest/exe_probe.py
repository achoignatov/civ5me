"""TEMPORARY diagnostic: build an instrumented copy of CivilizationV_DX11.exe that logs the wonder / city-art
path through OutputDebugStringA (visible in Proton's log with WINEDEBUG=+debugstr).

    python exe_probe.py build      # write build/rendertest/CivilizationV_DX11_probe.exe (game files untouched)
    python exe_probe.py install    # back up CivilizationV.exe and put the probe in its place (Steam's -applaunch
                                   # starts CivilizationV.exe, so this also makes test runs use DX11)
    python exe_probe.py restore    # put the original CivilizationV.exe / CivilizationV_DX11.exe back

Hooks (all code lives in a new section .rtdbg):
  A  0x4e1140 cvWonderLibrary instantiate entry:   "RTDBG I <caller> <count> <group> <art id>"
  B  0x4e12c2 its 'not initialized' failure:       "RTDBG F <group> <id> <count> <+0xcf4> <mesh bytes>"
  C  0x4dee60 city model group destroy:            "RTDBG D <caller> <group>"
"""
import hashlib
import os
import shutil
import struct
import sys

import keystone
import pefile

GAME = os.path.expanduser("~/.local/share/Steam/steamapps/common/Sid Meier's Civilization V")
DX11 = os.path.join(GAME, 'CivilizationV_DX11.exe')
DX9 = os.path.join(GAME, 'CivilizationV.exe')
BAKDIR = os.path.expanduser('~/civ5-exe-backup')
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'build', 'rendertest', 'CivilizationV_DX11_probe.exe')
DX11_SHA1 = 'cce934d589574312fbd66d217c919d178b3c0aa6'
SPRINTF, ODS = 0x939824, 0x9393f0
ks = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_32)


def sha1(p):
    return hashlib.sha1(open(p, 'rb').read()).hexdigest()


def asm(code, addr):
    return bytes(ks.asm(code, addr)[0])


def log_call(fmt_addr, pushes):
    """pushad/pushfd, sprintf(buf, fmt, args...) + OutputDebugStringA(buf), restore. `pushes` is asm that pushes the
    args (last arg first) with esp offsets valid right after 'sub esp,0x80' (the extra 0x24+0x80 is already in them)."""
    n = pushes.count('push')
    return f"""
      pushad; pushfd; sub esp,0x80
      {pushes}
      push {fmt_addr:#x}
      lea eax,[esp+{4 * (n + 1):#x}]; push eax
      call dword ptr [{SPRINTF:#x}]
      add esp,{4 * (n + 2):#x}
      push esp; call dword ptr [{ODS:#x}]
      add esp,0x80; popfd; popad
    """


def build():
    data = bytearray(open(DX11, 'rb').read() if sha1(DX11) == DX11_SHA1 else
                     open(os.path.join(BAKDIR, 'CivilizationV_DX11.exe'), 'rb').read())
    assert hashlib.sha1(data).hexdigest() == DX11_SHA1, 'unexpected exe version'
    pe = pefile.PE(data=bytes(data))
    base = pe.OPTIONAL_HEADER.ImageBase
    last = pe.sections[-1]
    sva = (last.VirtualAddress + last.Misc_VirtualSize + 0xfff) & ~0xfff
    sraw = (len(data) + 0x1ff) & ~0x1ff
    S = base + sva
    # strings first
    fmts = {'A': b'RTDBG I %x %d %d %d\0', 'B': b'RTDBG F %d %d %d %d %d\0', 'C': b'RTDBG D %x %d\0'}
    blob, fa = b'', {}
    for k, v in fmts.items():
        fa[k] = S + len(blob)
        blob += v
    blob = blob.ljust((len(blob) + 15) & ~15, b'\0')

    def off(va):
        return pe.get_offset_from_rva(va - base)
    hooks = []
    # A: entry of instantiate. ret +0xa4, arg1 +0xa8, arg2 +0xac (after the 4 pushes below the offsets shift)
    a_code = log_call(fa['A'], """
      mov eax,[esp+0xac]; push dword ptr [eax]
      mov eax,[esp+0xac]; push dword ptr [eax]
      push dword ptr [ecx+0x1fa50]
      push dword ptr [esp+0xb0]""") + "sub esp,0x1f0; push 0x4e1146; ret"
    hooks.append((0x4e1140, '81ecf0010000', a_code))
    # B: failure path, right before 'push edx; mov ecx,esi; call destroy'. arg2 ptr at [esp+0x208] there.
    b_code = """
      pushad; pushfd; sub esp,0x80
      mov eax,[esp+0x2ac]; mov eax,[eax]
      xor ebx,ebx; xor edi,edi
      cmp eax,[esi+0x1fa50]; jae skip
      imul ebx,eax,0xd10; add ebx,[esi+0x1fa4c]
      mov edi,[ebx+0x24]; sub edi,[ebx+0x20]; mov ebx,[ebx+0xcf4]
    skip:
      push edi; push ebx; push dword ptr [esi+0x1fa50]; push eax; push dword ptr [edx]
      push %s
      lea eax,[esp+0x18]; push eax
      call dword ptr [%s]
      add esp,0x1c
      push esp; call dword ptr [%s]
      add esp,0x80; popfd; popad
      push edx; mov ecx,esi
      push 0x4e12ca
      push 0x4dee60; ret
    """ % (hex(fa['B']), hex(SPRINTF), hex(ODS))
    hooks.append((0x4e12c2, '528bcee896dbffff', b_code))
    # C: city group destroy entry. ret +0xa4, arg ptr +0xa8
    c_code = log_call(fa['C'], """
      mov eax,[esp+0xa8]; push dword ptr [eax]
      push dword ptr [esp+0xa8]""") + "push esi; push edi; mov edi,[esp+0xc]; push 0x4dee66; ret"
    hooks.append((0x4dee60, '56578b7c240c', c_code))

    code = b''
    for site, orig, src in hooks:
        here = S + len(blob) + len(code)
        body = asm(src, here)
        o = off(site)
        assert bytes(data[o:o + len(orig) // 2]) == bytes.fromhex(orig), hex(site)
        j = asm(f'jmp {here:#x}', site)
        data[o:o + len(orig) // 2] = j.ljust(len(orig) // 2, b'\x90')
        code += body
    sec = (blob + code).ljust(0x1000, b'\xcc')
    data = data.ljust(sraw, b'\0') + sec
    # new section header
    pe = pefile.PE(data=bytes(data))
    hdr = pe.sections[-1].get_file_offset() + 40
    assert hdr + 40 <= pe.OPTIONAL_HEADER.SizeOfHeaders
    data[hdr:hdr + 40] = struct.pack('<8sIIIIIIHHI', b'.rtdbg\0\0', 0x1000, sva, 0x1000, sraw, 0, 0, 0, 0, 0x60000020)
    pe = pefile.PE(data=bytes(data))
    pe.FILE_HEADER.NumberOfSections += 1
    pe.OPTIONAL_HEADER.SizeOfImage = sva + 0x1000
    pe.OPTIONAL_HEADER.DllCharacteristics &= ~0x40          # no ASLR: the hooks use absolute addresses
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(pe.write())
    print('probe exe:', OUT, 'section .rtdbg at %#x, %d bytes of hooks' % (S, len(code)))


def install():
    os.makedirs(BAKDIR, exist_ok=True)
    for p in (DX9, DX11):
        b = os.path.join(BAKDIR, os.path.basename(p))
        if not os.path.exists(b):
            shutil.copy2(p, b)
    assert sha1(os.path.join(BAKDIR, 'CivilizationV_DX11.exe')) == DX11_SHA1
    shutil.copy2(OUT, DX9)
    print('installed probe (DX11) as', DX9)


def install_plain():
    """Put the UNMODIFIED DX11 exe in CivilizationV.exe's place (Steam's -applaunch starts CivilizationV.exe).
    2026-11-23: with the instrumented probe exe nothing in the palace slot drew, not even stock art."""
    os.makedirs(BAKDIR, exist_ok=True)
    for p in (DX9, DX11):
        b = os.path.join(BAKDIR, os.path.basename(p))
        if not os.path.exists(b):
            shutil.copy2(p, b)
    src = os.path.join(BAKDIR, 'CivilizationV_DX11.exe')
    assert sha1(src) == DX11_SHA1
    shutil.copy2(src, DX9)
    print('installed the plain DX11 exe as', DX9)


def restore():
    for p in (DX9, DX11):
        shutil.copy2(os.path.join(BAKDIR, os.path.basename(p)), p)
    assert sha1(DX11) == DX11_SHA1
    print('restored', DX9, 'and', DX11)


if __name__ == '__main__':
    {'build': build, 'install': install, 'install_plain': install_plain, 'restore': restore}[sys.argv[1]]()
