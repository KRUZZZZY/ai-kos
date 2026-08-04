pragma SPARK_Mode (On);

with AS_IO_Wrapper;  use AS_IO_Wrapper; 
with Digitpackage;  use Digitpackage; 
     
procedure Main is
   T  : Digit;

begin
   -- First we initialise standard_input and standard output
   AS_Init_Standard_Output;
   AS_Init_Standard_Input;   
   loop
      AS_Put("Enter a digit in 0 .. 9: ");   
      AS_Get(T,"Please type in an integer; please try again");
      exit when T in 0 .. 9;
      AS_Put_Line("Please Enter a number between 0 and 9");
   end loop;		     
end Main;
   

