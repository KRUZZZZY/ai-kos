with Example;
use Example;

procedure Main(X : in out Integer)
  with SPARK_MODE is
begin
   -- when checked with main.gpr
   --   causes error overflow check might fail
   -- when checked using mainWithoutRangeCheck.gpr
   --   no error
   X := f(2) + F + X;
end Main;
   

