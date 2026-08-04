pragma SPARK_Mode;

procedure One_Assert(X : in out Integer) is
begin
   X := X + 1;
   pragma Assert (X = 1);
   X := X + 1;
end One_Assert;

