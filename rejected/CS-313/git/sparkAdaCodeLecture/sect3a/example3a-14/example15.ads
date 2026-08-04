package Example15 is
   
   type Genders is (Male,Female);
   type Person is
      record
         YearOfBirth : Integer;
         Gender : Genders;
      end record;
   
   Sum : Integer:= 0;
   
   
   
   
   procedure Myproc(B: in Integer;
                    C: out Integer);
   
   function F(B,C : in Integer) return Integer;
   
   procedure ShowRecord(X : in Person);
   
   procedure ShowZ;
   
end Example15;
