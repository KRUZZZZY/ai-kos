pragma SPARK_Mode;

package body Example is
  
   procedure Test1(X : in Integer; Y : out Integer) is
   begin
      Y := X;
   end Test1;
   
   procedure Test2(X : in out Integer; Y : in out Integer) is
      T : Integer;
   begin
      T := X; X := Y; Y := T;
   end Test2;
   
   procedure Test3(Y : out Integer) is
   begin
      Y:= 2;
   end Test3;
   
   
   procedure Test4(X : out Integer; Y,Z : in Integer) is
   begin
      -- gnatprove reports overflow check error see README.txt
      X := Y + Z;
   end Test4;
   
   procedure Test5(X : in out Integer) is
   begin
      -- gnatprove reports overflow check error see README.txt      
      X := X + 1;
   end Test5;
   
   procedure Test6(X : in out Integer; Y : in Integer) is
   begin
      -- gnatprove reports overflow check error see README.txt           
      X := X + Y;
   end Test6;
   
end Example;
