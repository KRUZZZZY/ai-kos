with Example;
use Example;

procedure Main(X : in out Integer)
  with SPARK_MODE is
begin
   X := f + X;
end Main;
   

