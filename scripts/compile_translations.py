"""Utility: compile .po files into .mo files.

This script tries to use the system `msgfmt` (if available). If not, it will try to use `polib` (if installed).
Run: python scripts/compile_translations.py
"""
import os
import subprocess
import sys

root = os.path.dirname(os.path.dirname(__file__))
trans_root = os.path.join(root, 'app', 'translations')

failed = []
for lang in os.listdir(trans_root):
    lc = os.path.join(trans_root, lang, 'LC_MESSAGES')
    if not os.path.isdir(lc):
        continue
    for fn in os.listdir(lc):
        if not fn.endswith('.po'):
            continue
        po = os.path.join(lc, fn)
        mo = os.path.join(lc, fn[:-3] + '.mo')
        # Try msgfmt
        try:
            subprocess.check_call(['msgfmt', po, '-o', mo])
            print(f'Compiled {po} -> {mo} using msgfmt')
            continue
        except Exception:
            pass
        # Try polib
        try:
            import polib
            p = polib.pofile(po)
            p.save_as_mofile(mo)
            print(f'Compiled {po} -> {mo} using polib')
            continue
        except Exception:
            failed.append(po)

if failed:
    print('\nCould not compile the following .po files (install msgfmt or polib):')
    for p in failed:
        print(' -', p)
    sys.exit(1)
else:
    print('\nAll translations compiled successfully.')
