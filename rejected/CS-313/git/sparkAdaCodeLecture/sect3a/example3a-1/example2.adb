with Ada.Text_Io, Ada.Integer_Text_IO, Myfunction;
use Ada.Text_Io, Ada.Integer_Text_Io ;

  
procedure example2 is
   Number: Integer;
begin
   Get(Number); 
   Put( "Test " );
   Put("f(x)=");
   Put(Myfunction(Number));
   New_Line(1);
end Example2;

