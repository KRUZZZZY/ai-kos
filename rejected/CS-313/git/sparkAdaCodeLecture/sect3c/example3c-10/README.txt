gnatmake main.adb
has as result:
example.ads:9:16: no value supplied for component "B"
This might be due to a special restricted version of ada used for sparkada
consistent with the requirements of the ada compiler.

However, normal gcc gives the same error

gnatprove -P main.gpr --mode=flow
shows:
Phase 1 of 2: generation of Global contracts ...
example.ads:9:16: no value supplied for component "B"

gnatprove -P main.gpr --proof=per_path
gives the same error


