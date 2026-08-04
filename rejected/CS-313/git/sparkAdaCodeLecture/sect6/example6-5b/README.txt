This is same as example6-5, but with the file having an explicit ads file

gnatmake test.adb
 succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 succeeds


gnatprove -P main.gpr --proof=progressive
 reports a possible overflow problem:

test.adb:12:13: medium: overflow check might fail
   12 |      A:= A + 2;
      |          ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: subprogram at test.ads:7 should mention A in a precondition
    7 |   procedure Inc(A : in out Integer)
      |   ^ here
