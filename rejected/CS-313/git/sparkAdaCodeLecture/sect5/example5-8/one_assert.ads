Pragma SPARK_Mode;

procedure One_Assert(X : in out Integer)
  with 
    Depends => (X => X),
    Pre     => X = 0,
    Post    => X = 2;
   


