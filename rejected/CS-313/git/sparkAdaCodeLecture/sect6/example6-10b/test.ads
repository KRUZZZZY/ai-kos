pragma SPARK_Mode;

package Test is

   function F(X : Integer) return Integer is (X + 1) with
     Pre => X < Integer'Last;
     
   
   procedure Testproc(X : in Integer; Y : out Integer) with
     Depends => (Y => X),
     Pre  => X < Integer'Last,
     Post => Y = F(X);
   
end Test;

   

