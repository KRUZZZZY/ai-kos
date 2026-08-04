with Ada.Text_Io, Ada.Integer_Text_IO;
use Ada.Text_Io, Ada.Integer_Text_Io ;


Procedure Example6 is
   type Myarrayrange is new Integer range 0 .. 100;
   type Day is (Mon,Tue,Wed,Thu,Fri,Sat,Sun);
   type Myarraytype is array (Myarrayrange) of Day;
   type Vector is array (0 .. 100) of Integer;
   Myarray : Myarraytype;
   Myvector : Vector;
begin
   Myarray(17) := Fri;
   if Myarray(17) = Fri then
      Put_Line("Fri");
   else
      Put_Line("Not Fri");
   end if;
   MyVector(17) := 5;
   Put(MyVector(17));
     
end Example6;
  
     

