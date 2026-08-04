Pragma SPARK_Mode;

procedure Example(M,N : in out Integer)
  with 
    Depends => (M => M,
                N => (M,N)),
    Pre => (M > 0),
    Post => (M = 0 and N = M'Old + N'Old);
   


