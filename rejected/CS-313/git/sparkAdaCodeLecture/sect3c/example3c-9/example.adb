package body Example 
with SPARK_MODE is
   
   Function f(A : Integer := 3) return Integer
   is
      B : Integer:= A;
   begin
      loop 
         if B = 5 then
            return B+3;
         elsif B = 4 then 
            exit;
         end if;
         -- when checked with main.gpr
         --   causes error overflow check might fail
         -- when checked using mainWithoutRangeCheck.gpr
         --   no error
         B:= B + 1;
      end loop;
      return B;
   end F;
   
end Example;
