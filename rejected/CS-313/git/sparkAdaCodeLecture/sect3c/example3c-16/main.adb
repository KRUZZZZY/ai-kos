pragma SPARK_MODE(Off);
with Example;
use Example;

procedure Main(X : in out Boolean) is
begin
   -- compiling gives error because of potential aliasing problem.
   Exchange(X,X);
end Main;
   

