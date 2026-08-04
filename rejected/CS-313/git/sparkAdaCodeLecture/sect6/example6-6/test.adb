Pragma SPARK_Mode;

package body Test is
   
   procedure Init (A : out Integer) is
   begin
      A := 0;
   end Init;
	
     
   
   procedure Inc (A : in out Integer) is
   begin
      A:= A + 2;
   end Inc;

   
   Procedure Main (A : out Integer) is
   begin
      Init(A);
      Inc(A);
   end Main;

end Test;
