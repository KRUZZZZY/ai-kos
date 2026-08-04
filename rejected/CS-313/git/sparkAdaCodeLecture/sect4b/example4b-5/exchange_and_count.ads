Pragma SPARK_Mode;

procedure Exchange_And_Count(X,Y : in out Integer; Z : out Integer)
  with Depends => (X => Y,
                   Y => X,
                   Z => X);
   


