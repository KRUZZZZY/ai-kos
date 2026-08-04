pragma SPARK_MODE;
procedure Main(X : in out Boolean)
  with Depends => (X => X);


