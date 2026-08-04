gnatprove -P main.gpr --mode=flow
  succeeds
gnatprove -P main.gpr --proof=progressive
reports
  example.adb:17:16: medium: float overflow check might fail

gnatprove -P mainWithoutRangeCheck.gpr --proof=progressive
 reports the same error
There may be switch to modify mainWithoutRangeCheck.gpr
so this overflow error message is ignored, but I haven't found it yet.
If you find it please tell a.g.setzer@swansea.ac.uk








