in example.adb

line
Glob := Glob + X;
causes with     
   gnatprove -P main.gpr --mode=prove
error range condition failure

gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
succeeds
      
