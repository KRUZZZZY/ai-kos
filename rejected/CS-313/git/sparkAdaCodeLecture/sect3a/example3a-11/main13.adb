with Example13;
with Ada.Text_Io, Ada.Integer_Text_IO;
use Example13;
use Ada.Text_Io, Ada.Integer_Text_Io;

procedure Main13 is 
   D : Integer;

begin 
   --   Myproc(0);
   Myproc(0,D);
   Put("Afterwards D = ");
   Put(D);
   New_Line;
   Myproc(3+5,D);   
   Put("Afterwards D = ");   
   Put(D);
   New_Line;   
   Myproc(F(3,5),D);
   Put("Afterwards D = ");   
   Put(D);
   New_Line;      
end Main13;
