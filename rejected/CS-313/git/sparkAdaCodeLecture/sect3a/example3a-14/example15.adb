with Ada.Text_Io, Ada.Integer_Text_IO;
use Ada.Text_Io, Ada.Integer_Text_Io;

package body Example15 is
   
   X : Integer range 0 .. 1000;
   Z : Person;
   
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
      if X > 0
      then Put("X>0");
      else Put("X<=0");      
      end if;
   end MyProc;
   
   function F(B,C : in Integer) return Integer is
   begin
      return B * C;
   end F;
   
   procedure ShowRecord(X : in Person) is
   begin
      Put("year = ");
      Put(X.Yearofbirth);
      New_Line;
      Put("gender = ");
      if X.Gender = Male then
         Put("male");
      else 
         Put("female");
      end if;
      New_Line;      
   end ShowRecord;
   
   procedure ShowZ is
   begin
      ShowRecord(Z);
   end;

begin
   X := 10;
   Z.YearOfBirth:= 1970;
   Z.Gender := Male;
end Example15;

