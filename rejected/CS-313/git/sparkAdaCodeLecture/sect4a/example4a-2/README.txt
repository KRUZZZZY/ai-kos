running
    gnatprove -P main.gpr --mode=prove
reports error 

   example.adb:16:16: medium: overflow check might fail

running 
   gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
succeeds

