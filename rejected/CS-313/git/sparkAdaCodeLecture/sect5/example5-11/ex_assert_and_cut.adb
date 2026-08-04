pragma SPARK_Mode;

procedure Ex_Assert_And_Cut(X : in out Integer) is
   Xold : constant Integer := X;
begin
   pragma Assert_And_Cut (X = Xold);
   X := X + 1;
   pragma Assert_And_Cut (X = Xold + 1);
   X := X + 1;
   pragma Assert_And_Cut (X = Xold + 2);
   X:= X + 1;
end Ex_Assert_And_Cut;

