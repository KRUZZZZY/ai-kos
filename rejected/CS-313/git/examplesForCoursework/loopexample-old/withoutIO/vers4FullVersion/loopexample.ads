pragma SPARK_Mode;

package Loopexample is 
   
   procedure Loopproc (N : in Integer; Res : out Integer) with
     Depends => (Res => N),
     Pre  => (N in 0 .. 1000),
     Post => (Res = N);
   
   
end Loopexample;
