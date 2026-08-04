Pragma SPARK_Mode;

procedure Example(N,M : in out Integer)
  with Depends => (N => (N,M),
                   M => M),
  Pre => M >=0 and N < 0,
  Post => M = M'Old + 1;
  
   


