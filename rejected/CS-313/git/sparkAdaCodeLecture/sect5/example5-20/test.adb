pragma SPARK_Mode (On);
procedure Test (X: in out Integer) is
   Xold : constant Integer := X;
   U    : Integer := X;
begin
   U := U + 1;
   pragma Assert_And_Cut (U = Xold + 1);
   X:= U + 1;
end Test;

