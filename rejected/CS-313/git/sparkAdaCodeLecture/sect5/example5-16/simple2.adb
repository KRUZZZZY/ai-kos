pragma SPARK_Mode (On);
procedure Simple2 (X: in out Integer) is
begin
   if X > 1
   then X := -1;
      pragma Assert (X = 1);
   else X := 2;
      pragma Assert (X = 2);   
   end if;
end Simple2;

