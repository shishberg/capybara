#!/bin/zsh
# Every table probe on the right half of one preset (the wells probes only
# when it has wells), plus mirror.py for the left.
# usage: AUDIT_REPO=... run_all.sh <preset>
here=${0:A:h}
export AUDIT_PRESET=$1
: ${AUDIT_REPO:?set AUDIT_REPO to the checkout under audit}
probes=(namecheck.py mesh_validity.py voids.py mirror.py plinth.py screws.py ports.py parts_fit.py
        pockets.py room_gaps.py part_gap.py switches_caps.py capgap.py way_free.py ways_in.py
        tile_path_gap.py overhang.py print3mf.py "thickness.py body" "thickness.py plate")
wells=$(cd $AUDIT_REPO && .venv/bin/python -c "from case import build as B, params as P; B.set_params([], '$1'); print(P.well_depth_mm > 0)")
[ "$wells" = True ] && probes+=(wells.py well_holes.py)
for p in $probes; do
  $here/run_bounded.sh right ${=p}
done
