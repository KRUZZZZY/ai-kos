pragma SPARK_Mode;
with Ada.Text_Io, Ada.Integer_Text_IO;
use Ada.Text_Io, Ada.Integer_Text_IO;


procedure Main is
   X : Integer;
   User_Input : String(1 .. 20);
   Last : Integer;
begin
   loop	
      Put("Enter a Number: ");
      Get(X);	
      X := X + 1;			
      New_Line;
      Put(X);	
      New_Line;      		
      -- The following lines don't pass SPARK Ada checks because we are not using
      -- the SPARK Ada library for IO
      Get_Line(User_Input, Last);  -- clearing input buffer
      Put("Do you want to try again (y/n):");
      Get_Line(User_Input, Last);
      exit when User_Input(1 .. 1) = "n" and Last > 0;
   end loop;   
end Main;


