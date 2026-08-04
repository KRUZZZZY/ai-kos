pragma SPARK_Mode;

package body Loopexample is 
   
   procedure Loopproc (N : in Integer; Res : out Integer) is
   begin
      Res := 0;
      loop   
         exit when Res = N;
         -- sparkada reports overflow check might fail
         -- see README.txt
         Res := Res + 1;
      end loop;
   end loopproc;
      
end Loopexample;   

