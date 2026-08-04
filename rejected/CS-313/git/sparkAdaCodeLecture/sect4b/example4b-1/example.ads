Pragma SPARK_Mode;

package Example is
  
   procedure Test1(X : in Integer; Y : out Integer) 
     with Depends => (Y => X);
   
   procedure Test2(X : in out Integer; Y : in out Integer)
     with Depends => (X => Y,
                      Y => X);


   procedure Test3(Y : out Integer)
     with Depends => (Y => null);
   
   procedure Test4(X : out Integer; Y,Z : in Integer)
     with Depends => (X => (Y,Z));

   procedure Test5(X : in out Integer)
     with Depends => (X => X);


   procedure Test6(X : in out Integer; Y : in Integer)
     with Depends => (X => (X,Y));
   
end Example;


