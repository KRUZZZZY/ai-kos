with as_io_wrapper; use As_Io_Wrapper;


procedure Example
  with SPARK_MODE

is
   A : Integer := 0;
begin
   loop 
      if A = 5 then
         As_Put_Line(A);
         return;
      end if;
      A := A + 1;
      -- gnatprove -P main.gpr --mode=prove
      --   fails because of possible out of range error
      -- gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
      --   succeeds (no range check)
      As_Put_Line(A);      
   end loop;
end Example;
