with Text_Io;
use text_io;

procedure Testparameterpassing4 is

   type Testrecord is
      record
         A : String(1 .. 1);
         B : Integer;
      end record;

   X : Testrecord;
   Y : Testrecord;

   -- Compiling this procedure will fail, which is correct behaviour of ada.
   -- in parameters cannot be modified
   procedure Exchange (x : in Testrecord ; y : in Testrecord) is
      tmp : Testrecord;
   begin
      tmp := X;
      X := Y;
      Y := Tmp;
   end Exchange;

begin
   X := ("X",1);
   Y := ("Y",2);
   Exchange(X,Y);
   Put_Line(X.A);
   Put_Line(Y.A);
end Testparameterpassing4;


