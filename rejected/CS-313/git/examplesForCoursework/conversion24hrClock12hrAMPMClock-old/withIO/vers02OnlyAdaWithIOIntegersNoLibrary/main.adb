pragma SPARK_Mode;
with Ada.Text_Io, Ada.Integer_Text_IO, Clock;
use Ada.Text_Io, Ada.Integer_Text_Io, Clock;


procedure Main is
   T , U : Integer;
   User_Input : String(1 .. 20);
   Last : Integer;
begin
   loop
      loop
         Put("Enter a number in hour from 0 .. 23: ");   
         Get(T);
         exit when T in 0 .. 23;
         Put_Line("Please Enter a number between 0 and 23");
      end loop;
      Put("The result of the function  is ");
      Put(To12(T));
      New_Line;   
      To12Proc(T,U);
      Put("The result of the procedure is ");
      Put(U);   
      New_Line;   
      Put_Line("Note that this program is not the correct conversion from 24hrs to am/pm"); 
      Put_Line("See ../README.txt for details");
      -- The following lines don't pass SPARK Ada checks because we are not using
      -- the SPARK Ada library for IO
      Get_Line(User_Input, Last);  -- clearing input buffer
      Put("Do you want to try again (y/n):");
      Get_Line(User_Input, Last);
      exit when User_Input(1 .. 1) = "n";
   end loop;   
end Main;


