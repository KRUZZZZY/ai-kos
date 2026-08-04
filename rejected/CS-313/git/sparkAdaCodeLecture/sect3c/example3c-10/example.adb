package body Example 
with SPARK_MODE is
   
   Function f return Integer
   is
      
   begin
      if X.A = 3 then
         return 7;
      else 
         return 6;
      end if;
   end F;
   
end Example;
