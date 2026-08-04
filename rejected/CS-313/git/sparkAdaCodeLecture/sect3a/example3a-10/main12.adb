with Ada.Text_IO; use Ada.Text_IO;

with Example12;

procedure Main12 is 
   C : Integer := 3;

begin 
   --   Myproc(0);
   Example12.Myproc(C);
   if C = 0 
   then Put("C=0"); 
   else Put("C != 0"); 
   end if;
      
end Main12;
