gnatmake main.adb
  succeeds
gnatprove -P mainWithoutRangeCheck.gpr --proof=per_path
  succeeds

gnatprove -P main.gpr --proof=per_path
   reports possible overflow errors (corrected in vers4)

loopexample.adb:15:24: medium: overflow check might fail
   15 |            Res := Res + 2;
      |                   ~~~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer

loopexample.ads:9:52: medium: overflow check might fail
    9 |     Post => (Res = 2 * I and N <= Res and Res < N + 2);
      |                                                 ~~^~~
  reason for check: result of addition must fit in a 32-bits machine integer




