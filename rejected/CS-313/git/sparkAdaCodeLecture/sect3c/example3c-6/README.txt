line with A:= A+1:

   checking using
      gnatprove -P main.gpr --mode=prove
   causes error: overflow check might fail
  
   checking using
      gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
   succeeds
