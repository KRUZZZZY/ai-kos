function Example return Integer
  with SPARK_MODE

is
   A : Integer := 0;
begin
   loop 
      if A = 5 then
         return A+3;
      elsif A = 4 then 
         exit;
      end if;
      -- checking using
      --    gnatprove -P main.gpr --mode=prove
      -- causes error: overflow check might fail
      -- checking using
      --     gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
      -- succeeds
      A:= A + 1;
   end loop;
   return A;
end Example;
