pragma SPARK_Mode;

procedure Example(M,N : in out Integer) is
begin
   loop
      pragma Loop_Invariant (M + N = M'Loop_Entry + N'Loop_Entry and M > 0); 
      M := M - 1;
      N := N + 1;
      exit when M <= 0;
   end loop;
end Example;

