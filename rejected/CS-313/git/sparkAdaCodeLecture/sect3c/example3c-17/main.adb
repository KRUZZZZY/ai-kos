pragma SPARK_MODE;
with Example;
use Example;

procedure Main(X : in out Boolean) 
is  
   Y : Boolean := True;
begin
   -- gnatprove -P main.gpr --mode=flow
   -- gives error
   -- because you cannot use Exchange with spark_mode off from
   -- a file with speark_mode on
   Exchange(X,Y);
   -- gnatprove -P main.gpr --mode=flow
   -- gives error
   -- because variables might be in wrong order
   --
   -- gnatprove -P main.gpr --mode=flow
   -- gives error
   -- because you cannot use Exchange with spark_mode off from
   -- a file with speark_mode on
   --
   -- if we put in example.adb and example.ads spark_mode(on)
   -- then the previous errors about Exchange not allowed to be used
   --       disappear 
   -- but it detects
   --    Y is changed but not used after the call
   --
   Exchange(Y,X);      
   
end Main;
   

