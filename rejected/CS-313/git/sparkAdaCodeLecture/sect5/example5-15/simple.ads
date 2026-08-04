pragma SPARK_Mode (On);
procedure Simple (X: in out Integer)
  with
    Depends => (X => X),
    Pre =>  (X < 0),
    Post => (X  > 0);

