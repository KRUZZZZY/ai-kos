gnatmake succeeds (although there is a recursion)

gnatprove -P main.gpr --proof=per_path

detects an overflow check in

example.adb:13:23: medium: overflow check might fail
example.adb:13:28: medium: overflow check might fail
example.adb:26:18: medium: overflow check might fail

which is due to increasing or decreasing integers without any
restrictions


gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
succeeds (no range check)
