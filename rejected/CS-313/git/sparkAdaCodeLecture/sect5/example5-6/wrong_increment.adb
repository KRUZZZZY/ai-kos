pragma SPARK_Mode;

procedure Wrong_Increment(X : in out Integer) is
begin
   X := X + X;
end Wrong_Increment;

