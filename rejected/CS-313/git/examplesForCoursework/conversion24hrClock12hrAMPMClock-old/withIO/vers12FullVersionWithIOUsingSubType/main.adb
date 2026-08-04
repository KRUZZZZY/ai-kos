pragma SPARK_Mode (On);

with AS_IO_Wrapper;  use AS_IO_Wrapper; 
with Clock;  use Clock; 


procedure Main is
   User_Input_Int : Integer;
   U : Hour12;
   T : Hour;
   User_Input : String(1 .. 20);
   Last : Integer;

begin
   -- First we initialise standard_input and standard output
   AS_Init_Standard_Output;
   AS_Init_Standard_Input;   
   loop
      loop
         AS_Put("Enter a number in hour from 0 .. 23: ");   
         AS_Get(User_Input_Int,"Please type in an integer; please try again");
         exit when User_Input_Int in 0 .. 23;
         AS_Put_Line("Please Enter a number between 0 and 23");
      end loop;
      T  := User_Input_Int;
      U:= To12(T);
      AS_Put("The result of the function  is ");
      AS_Put_Line(U);
      To12Proc(T,U);
      AS_Put("The result of the procedure is ");
      AS_Put_Line(U);   
      AS_Put_Line("Note that this program is not the correct conversion from 24hrs to am/pm"); 
      AS_Put_Line("See ../README.txt for details");     
      loop
         As_Put("Do you want to try again (y/n)? ");
         As_Get_Line(User_Input, Last);
         exit when Last > 0;
         As_Put_Line("Please enter a non-empty string");
      end loop;
      exit when User_Input(1 .. 1) = "n";
   end loop;        
end Main;
   

