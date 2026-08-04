pragma SPARK_MODE(Off);
with Example;
use Example;

procedure Main(X : in out Boolean) 
is  
   Y : Boolean := True;
begin
   Exchange(X,Y);
   -- even though we have SPARK_MODE(off) 
   -- the  next line doesn't pass 
   --    gnatprove -P main.gpr --mode=flow
   -- because it says: arguments may be in wrong order
   --   if one uses variables A,B instead of X,Y 
   --   there is no problem
   -- this is an example of a more sophisticated SPARK Ada check
   Exchange(Y,X);      
end Main;
   

