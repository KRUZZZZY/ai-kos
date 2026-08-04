package body Example 
with SPARK_MODE 
is
   procedure Exchange(X : in out Boolean;  Y : in out Boolean) is
   begin   
      if X /= Y then
         X := X xor Y;
         Y := X xor Y;      
         X := X xor Y;   
      end if;
   end Exchange;   
   
   procedure Wrong_Exchange(X : in out Boolean;  Y : in out Boolean) is
   begin   
      X := X xor Y;
      Y := X xor Y;      
      X := X xor Y;   
     
   end Exchange; 
   
end Example;

