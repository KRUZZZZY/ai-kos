Pragma SPARK_Mode;

procedure Exchange_And_Count2(X,Y,Z : in out Integer)
  with Depends => (X => Y,
                   Y => X,
                   Z => (Z,X));
   


