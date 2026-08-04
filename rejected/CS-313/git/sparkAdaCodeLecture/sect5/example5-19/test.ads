pragma SPARK_Mode (On);
procedure Test (X: in out Integer)
  with
    Depends => (X => X),
    Post => (X  = X'Old + 3);
