pragma SPARK_Mode;

procedure Test(X : in out Integer)
  with Depends => (X => X),
       Pre => (X > 0),
       Post => (X > 3);
   

