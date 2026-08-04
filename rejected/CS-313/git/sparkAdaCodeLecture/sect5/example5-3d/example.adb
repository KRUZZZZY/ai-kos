pragma SPARK_Mode;

package body Example is
   

   procedure Example1(N : in Integer;M : in out Integer) is
   begin
      M := M + N;
   end Example1;
   
end Example;

