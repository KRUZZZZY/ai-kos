with Text_Io;
use text_io;

procedure Testparameterpassing2 is

   type Testrecord is
      record
         A : String(1 .. 1);
         B : Integer;
      end record;

   X : Testrecord;
   Y : Testrecord;

   procedure Exchange (x : in out Testrecord ; y : in out Testrecord) is
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
end Testparameterpassing2;


