-- pragma SPARK_MODE;
--    not needed because of line  below
--        with SPARK_MODE is   
-- with SPARK.Text_IO; use SPARK.Text_IO;

package body Example 
with SPARK_MODE is   
   
   function f(A : Integer) return Integer is
   begin
      if A = 3 then
         return 7;
      else
         return 9;
      end if;
   end F;
   
   function f(A : Angle) return Integer is
   begin
      if A = 3 then
         return 4;
      else
         return 8;
      end if;      
   end F;

   

end Example;
