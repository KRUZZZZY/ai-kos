gnatprove -P main.gpr --mode=prove
reports
   example.adb:15:18: medium: overflow check might fail
gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
  succeeds

Note:
A previous version of Spark Ada detected an infinite loop.
Spark ada 2021 doesn't detect this anymore
