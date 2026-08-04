gnatmake exchange_and_count.adb
  succeeds without errors

gnatprove -P main.gpr --mode=flow
reports data flow errors

exchange_and_count.ads:6:20: medium: missing dependency "Z => X"
    6 |                   Z => Z);
      |                   ^ here

as discussed in the lecture

gnatprove -P main.gpr --proof=per_path
reports this error and in addition an overflow error

exchange_and_count.adb:6:34: medium: overflow check might fail
    6 |   T := X; X:= Y; Y := T; Z := Z + T;
      |                               ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at exchange_and_count.ads:3 should mention Z in a precondition
    3 |procedure Exchange_And_Count(X,Y,Z : in out Integer)
      |^ here



gnatprove -P mainWithoutRangeCheck.gpr --proof=per_path
reports only the flow error.

See 
example4b-2corrected/
for the corrected version of this program

