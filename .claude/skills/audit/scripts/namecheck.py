"""Which case names the audit scripts use are missing at HEAD: every
`A.X.name` and, in a file that aliases the modules (`S, C = A.S, A.C`, or
`import case.chassis as C`), every `X.name` too, for X in S C R L P B.

    python namecheck.py      (prints nothing when every name exists)
"""
import glob
import os
import re

import common as A

mods = dict(S=A.S, C=A.C, R=A.R, L=A.L, P=A.P, B=A.B)
here = os.path.dirname(os.path.abspath(__file__))
for f in sorted(glob.glob(os.path.join(here, "*.py"))):
    src = open(f).read()
    aliased = set(re.findall(r"\b([SCRLPB])\b(?=[^=\n]*=\s*A\.)", src)) | set(re.findall(r"import case\.\w+ as ([SCRLPB])\b", src))
    names = set(re.findall(r"\bA\.([SCRLPB])\.([A-Za-z_]\w*)", src))
    names |= {(m, n) for m, n in re.findall(r"(?<![\w.])([SCRLPB])\.([A-Za-z_]\w*)", src) if m in aliased}
    for m, n in sorted(names):
        if not hasattr(mods[m], n):
            print(os.path.basename(f), f"{m}.{n}")
