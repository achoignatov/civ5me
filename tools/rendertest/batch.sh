#!/bin/bash
# usage: batch.sh <label> <runs> [build_dlc flags...]   (temporary render-test helper)
cd "$(dirname "$0")/../.."
label=$1; runs=$2; shift 2
python3 tools/build_dlc.py --rendertest "$@" > /dev/null || { echo BUILD FAILED; exit 1; }
for n in $(seq 1 $runs); do
  timeout 900 build/venv/bin/python tools/rendertest/rendertest.py run ${label}_$n 2>&1 | grep -E "RT_PLAYNOW|RT_SHOT 1 |RT_ERROR|Runtime|CRASH|restored"
  d=$(ls -dt build/rendertest/shots/*_${label}_$n | head -1)
  echo "majors=$(awk '/placing major/{f=1;next}/placing city-states/{f=0}f' $d/Lua.log | wc -l)"
  build/venv/bin/python tools/rendertest/sheet.py $d
  sleep 5
done
echo BATCH_END $label
