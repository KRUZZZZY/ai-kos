with Example15;
with Ada.Text_Io, Ada.Integer_Text_IO;
use Example15;
use Ada.Text_Io, Ada.Integer_Text_Io;

procedure Main15 is 
   D : Integer;
   E : Person;
   E2 : Person;   

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
   Put("Sum = ");
   Put(Sum);
   New_Line;    
   Put_line("Showing Z");
   ShowZ;
   E := (1983,FeMale);
   Put_line("Showing E");   
   ShowRecord(E);   
   E2 := (Gender => Female,Yearofbirth=> 2030);
   Put_line("Showing E2");      
   Showrecord(E2);
end Main15;
