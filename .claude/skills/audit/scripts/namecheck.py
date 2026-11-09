"""Which lowpro names the audit scripts use are missing at HEAD."""
import re, glob
import common as A
mods = dict(S=A.S, C=A.C, R=A.R, L=A.L, P=A.P, B=A.B)
for f in sorted(glob.glob("*.py")):
    for m, n in sorted(set(re.findall(r"\bA\.(S|C|R|L|P|B)\.([A-Za-z_]+)", open(f).read()))):
        if not hasattr(mods[m], n):
            print(f, f"{m}.{n}")
