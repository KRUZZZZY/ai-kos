Correction of example-4b (except for overflow error which will be discussed in 
    sect 5 )

gnatmake exchange_and_count.adb
  succeeds without problems

gnatprove -P main.gpr --mode=flow
and
gnatprove -P mainWithoutRangeCheck.gpr --proof=per_path
succeed without errors

exchange_and_count.adb:9:34: medium: overflow check might fail
    9 |   T := X; X:= Y; Y := T; Z := Z + 1;
      |                               ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at exchange_and_count.ads:3 should mention Z in a precondition
    3 |procedure Exchange_And_Count(X,Y,Z : in out Integer)
      |^ here

