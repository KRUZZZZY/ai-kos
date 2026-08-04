gnatmake exchange_and_count2.adb
  succeeds without errors

gnatprove -P mainWithoutRangeCheck.gpr  --proof=per_path
passes everything as does
gnatprove -P main.gpr --mode=flow


gnatprove -P main.gpr --proof=per_path

reports a possible overflow problem:

exchange_and_count2.adb:7:34: medium: overflow check might fail
    7 |   T := X; X:= Y; Y := T; Z := Z + T;
      |                               ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at exchange_and_count2.ads:3 should mention Z in a precondition
    3 |procedure Exchange_And_Count2(X,Y,Z : in out Integer)
      |^ here



