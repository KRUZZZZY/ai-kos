Pragma SPARK_Mode;

procedure Ex_Assert_And_Cut(X : in out Integer)
  with 
    Depends => (X => X),
    Pre     => X = 0,
    Post    => X = 3;
   


