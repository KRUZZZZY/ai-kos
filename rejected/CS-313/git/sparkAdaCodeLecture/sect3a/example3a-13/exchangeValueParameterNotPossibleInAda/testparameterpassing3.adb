with Text_Io;
use text_io;

procedure Testparameterpassing3 is

   type Testrecord is
      record
         A : String(1 .. 1);
         B : Integer;
      end record;

   X : Testrecord;
   Y : Testrecord;

   -- Compiling this procedure will fail, which is correct behaviour of ada.
   -- record fields of an in parameter cannot be modified
   procedure Exchange (x : in Testrecord ; y : in Testrecord) is
      tmp : String(1 .. 1);
   begin
      tmp := X.A;
      X.A := Y.A;
      Y.A := Tmp;
   end Exchange;

begin
   X := ("X",1);
   Y := ("Y",2);
   Exchange(X,Y);
   Put_Line(X.A);
   Put_Line(Y.A);
end Testparameterpassing3;


