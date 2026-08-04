gnatmake decrease_increase.adb
   returns no error
gnatprove -P mainWithoutRangeCheck.gpr  --proof=per_path
  reports no errors
gnatprove -P main.gpr  --mode=flow
  reports no errors

gnatprove -P main.gpr --proof=per_path
reports a possible overflow problem

decrease_increase.adb:9:25: medium: overflow check might fail
    9 |     X := X - 1; Y := Y + 1;
      |                      ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer
  possible fix: loop at line 5 should mention Y in a loop invariant
    5 |  loop
      |  ^ here


