pragma SPARK_Mode (On);

with AS_IO_Wrapper;  use AS_IO_Wrapper; 


procedure Test_Integer_IO is
   X : Integer;
begin
   -- First we initialise standard_input and standard output
   AS_Init_Standard_Output;
   AS_Init_Standard_Input;   
   -- Print on screen "Type in some number"
   AS_Put_Line("Type in some number");
   -- ask for an  integer (in variable X) until an integer has been entered
   --   if something else has been entered ask again
   AS_Get(X,"Please type in an integer; please try again");
   -- Print out the resultx
   AS_Put_Line("You typed in");
   AS_Put(X);
end Test_Integer_IO;     
   

