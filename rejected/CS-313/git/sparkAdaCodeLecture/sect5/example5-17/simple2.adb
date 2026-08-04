pragma SPARK_Mode (On);
procedure Simple2 (X: in out Integer) is
begin
   if X > 1
   then X := -1;
      pragma Assert_And_Cut (X = 1);
   else X := 2;
      pragma Assert_And_Cut (X = 2);   
   end if;
end Simple2;

