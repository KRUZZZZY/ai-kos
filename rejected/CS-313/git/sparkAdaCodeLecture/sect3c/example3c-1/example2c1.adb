package body Example2c1  
with SPARK_MODE

  
is
   -- We get an error when checking with Spark Ada
   -- since functions having side effects are not allowed
   Function F(X : Integer) return  Integer
   is
   begin
      Z := 0;
      return X;
   end F;
   
   

end Example2c1;
