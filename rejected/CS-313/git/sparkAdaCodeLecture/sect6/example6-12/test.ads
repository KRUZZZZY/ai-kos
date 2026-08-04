pragma SPARK_Mode;

package Test is
   
   function Cond(X, Y : Integer) return Boolean is (X <= Y);
   
   procedure Test1 (X,Y : in out Integer) with
     Depends => (X => X,
                 Y => Y),
     Pre => (Cond(X,Y) and X <= 10000 and Y <= 10000),
     Post => Cond (X,Y);
   
end Test;
	   
   
   

     

   

