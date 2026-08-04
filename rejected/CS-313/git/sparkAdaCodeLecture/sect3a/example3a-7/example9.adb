with Ada.Text_Io, Ada.Integer_Text_IO,Float_Text_Io;
use Ada.Text_Io, Ada.Integer_Text_Io,Float_Text_Io;


Procedure Example9 is
   X : Float := 3.0;
   Y : Float := 3.0;   
begin
   for N in 1 .. 20 loop
      Put (N);
   end loop;
   New_Line(1);         
   Put_Line("float loop");
   while (X > 0.0) loop
      Y:= Y + 1.0;
      X := X - 1.0;
      exit when Y > 5.0;
      Put ("X = ");
      Put(X,1);
      New_Line(1);      
      Put ("Y = ");
      Put (Y,1);
      New_Line(1);            
   end loop;
   Put_Line("Finished");
   Put ("X = ");
   Put(X,1);
   New_Line(1);         
   Put ("Y = ");   
   Put (Y,1);
   New_Line(1);         
      
end Example9;
  
     

