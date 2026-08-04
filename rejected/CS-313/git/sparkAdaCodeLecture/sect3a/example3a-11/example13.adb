with Ada.Text_Io, Ada.Integer_Text_IO;
use Ada.Text_Io, Ada.Integer_Text_Io;

package body Example13 is
   
   
   procedure Myproc(B: in Integer;
                    C: out Integer) is   
   begin
      Put("B=");
      Put(B);
      New_Line;
      C := B;
      Put("C=");      
      Put(C);
      New_Line;      
   end MyProc;
   
   function F(B,C : in Integer) return Integer is
   begin
      return B * C;
   end F;


end Example13;

