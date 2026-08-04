pragma SPARK_Mode (On);
procedure Test (X: in out Integer) is
   Xold : constant Integer := X;
begin
   X := X + 1;
   pragma Assert_And_Cut (X = Xold + 1);
   X:= X + 1;
end Test;

