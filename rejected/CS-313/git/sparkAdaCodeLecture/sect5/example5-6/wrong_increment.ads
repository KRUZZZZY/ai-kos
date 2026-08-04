Pragma SPARK_Mode;

procedure Wrong_Increment(X : in out Integer)
  with 
    Depends => (X => X),
    Pre     => X >= 0,
    Post    => X = X'Old + 1 and X >= 1;



