pragma SPARK_MODE;
With Example;
use Example;

procedure Main(X : in out Boolean) is
begin
   -- the following fails because of aliasing problem
   -- error: writable actual for "X" overlaps with actual for "Y"
   Exchange(X,X);
end Main;
   

