pragma SPARK_Mode;

package Loopexample is 
   
   procedure Loopproc (N : in Integer; Res : out Integer) with
     Depends => (Res => N);
   
   
end Loopexample;
