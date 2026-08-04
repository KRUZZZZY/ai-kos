pragma SPARK_MODE;
With Example; use Example;
with AS_IO_Wrapper;  use AS_IO_Wrapper; 

procedure Main is
   X,Y : Boolean := True;
begin
   AS_Init_Standard_Output;
   AS_Init_Standard_Input; 
   -- the following fails because of aliasing problem
   -- error: writable actual for "X" overlaps with actual for "Y"
   Exchange(X,X);
   if X then
      AS_Put("Result of Exchange(X,X) is X = True");
   else
      AS_Put("Result of Exchange(X,X) is X = False");
   end if;
   
   -- the following fails because of aliasing problem
   -- error: writable actual for "X" overlaps with actual for "Y"
   Wrong_Exchange(Y,Y);
   if Y then
      AS_Put("Result of Wrong_Exchange(Y,Y) is Y = True");
   else
      AS_Put("Result of Wrong_Exchange(Y,Y) is Y = False");
   end if;
   
end Main;
   

