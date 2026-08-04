Pragma SPARK_Mode;

package body Test is
   
   procedure Init is
   begin
      A := 0;
   end Init;
	
     
   
   procedure Procedure1 is
   begin
      A:= A + 2;
   end Procedure1;

   
   Procedure Main is
   begin
      Init;
      Procedure1;
   end Main;

end Test;
