gnatmake main.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr  --proof=per_path
and
gnatprove -P main.gpr --mode=flow
both succeed


gnatprove -P main.gpr --proof=per_path

reports possible overflow errors:

loopexample.adb:13:20: medium: overflow check might fail
   13 |            I := I + 1;
      |                 ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: loop at line 10 should mention I in a loop invariant
   10 |         loop
      |         ^ here

loopexample.adb:14:24: medium: overflow check might fail
   14 |            Res := Res + 2;
      |                   ~~~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: loop at line 10 should mention Res in a loop invariant
   10 |         loop
      |         ^ here

