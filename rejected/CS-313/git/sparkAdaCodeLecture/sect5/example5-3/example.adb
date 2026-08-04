pragma SPARK_Mode;

package body Example is
   

   procedure Example1(N,M : in out Integer) is
   begin
      if M < 0 then
         N := N - 1;
         M := M + 1;
      else
         N := N + 1;
         M := M - 1;
      end if;
   end Example1;
   
end Example;

