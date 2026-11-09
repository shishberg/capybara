#!/bin/zsh
# Runs one probe with its memory watched, killing it past 2 GB.
# usage: AUDIT_REPO=... AUDIT_PRESET=... run_bounded.sh <half> <probe.py> [args]
#   -> out/<preset>/<probe>-<half>[-<first arg>].txt beside this script, and the peak RSS on stdout.
# Works from any working directory: the probe and out/ are found beside this script.
here=${0:A:h}
half=$1; probe=$2; shift 2
dir=$here/out/$AUDIT_PRESET; mkdir -p $dir
out="$dir/${probe%.py}-$half${1:+-$1}.txt"
AUDIT_HALF=$half $AUDIT_REPO/.venv/bin/python $here/$probe "$@" > $out.raw 2>&1 &
pid=$!
peak=0
while kill -0 $pid 2>/dev/null; do
  r=$(ps -o rss= -p $pid 2>/dev/null)
  [ -n "$r" ] && [ "$r" -gt "$peak" ] && peak=$r
  [ -n "$r" ] && [ "$r" -gt 2000000 ] && { echo "KILLED $probe $half at ${r} kB"; kill $pid; }
  sleep 1
done
wait $pid; code=$?
grep -v "Warning\|center_mass\|integrated\|inertia\|denominator\|barycentric" $out.raw > $out; rm $out.raw
echo "$probe $half $1: exit $code, peak RSS $((peak/1024)) MB -> $out"
