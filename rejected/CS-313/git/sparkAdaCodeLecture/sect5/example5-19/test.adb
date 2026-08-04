pragma SPARK_Mode (On);
procedure Test (X: in out Integer) is
   U    : Integer;
begin
   X := X + 1;
   U := X + 1;
   pragma Assert_And_Cut (U = X + 1);
   X:= U + 1;
end Test;

