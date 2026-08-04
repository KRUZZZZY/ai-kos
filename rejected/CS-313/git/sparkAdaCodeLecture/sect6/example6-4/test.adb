Pragma SPARK_Mode;

package body Test is
   
   procedure Init (A : out Integer) is
   begin
      A := 0;
   end Init;
	
     
   
   procedure Inc2 (A : in out Integer) is
   begin
      A:= A + 2;
   end Inc2;

   
   Procedure Main (A : out Integer) is
   begin
      Init(A);
      Inc2(A);
   end Main;

end Test;
