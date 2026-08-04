pragma SPARK_MODE;
with as_io_wrapper; use as_io_wrapper;

package body Main 
is

   procedure A1
   --     with Refined_Global => ((Output => Glob),
   --			     (In_Out => Standard_Output))
   is  
      Y : Integer := 5;
   begin
      Init;
      while (Y > 0) loop
         Y := A1(Y);
         As_Put_Line;
      end loop;
   end A1;

end Main;
   

