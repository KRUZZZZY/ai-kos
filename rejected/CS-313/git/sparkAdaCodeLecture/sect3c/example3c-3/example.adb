with As_Io_Wrapper;  use As_Io_Wrapper; 


procedure Example
  with SPARK_MODE

is
   A : Integer := 0;
begin
   Outer: loop 
      if A = 5 then
         if A + 0 = 6 then  
            As_Put_Line(A);
            exit outer;
         end if;
      end if;
      -- gnatprove -P main.gpr --mode=prove
      --   fails because of possible out of range error
      -- gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
      --   succeeds (no range check)
      A := A + 1;
      AS_Put_Line(A);
   end loop Outer;
end Example;
