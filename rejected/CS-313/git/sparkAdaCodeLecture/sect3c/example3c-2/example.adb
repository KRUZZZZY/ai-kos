with as_io_wrapper; use as_io_wrapper;


procedure Example
  with SPARK_MODE

is
   A : Integer := 0;
begin
   loop 
      if A = 5 then
         AS_Put_Line(A);
         exit;
      end if;
      -- gnatprove -P main.gpr --mode=prove
      --    fails because of a possible out of range error
      -- gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
      --   succeeds (no range condition check)      
      -- gnatprove -P main.gpr --mode=flow
      --   succeeds (only flow analysis)
      A := A + 1;
      AS_Put_Line(A);
   end loop;
end Example;
