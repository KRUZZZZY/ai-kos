--pragma SPARK_Mode (Off);

with AS_IO_Wrapper;  use AS_IO_Wrapper; 
-- Import junction package and bring its procedures 
-- into this namespace

with junction;  use junction; 

procedure Main is
   D, E: Integer;

begin
   AS_Put("Enter an integer");
   AS_Get(D, "Please type in an integer; please try again");
   
   -- call the procedure
   sideEffect(SmInteger(D), SmInteger(E));
   AS_Put("The result of sideEffect procedure is ");
   AS_Put_Line(E);

   
end Main;
