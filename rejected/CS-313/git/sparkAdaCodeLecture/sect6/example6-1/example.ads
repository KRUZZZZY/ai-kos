Pragma SPARK_Mode;

procedure Example(M,N : in out Integer)
  with 
    Depends => (M => M,
                N => (M,N)),
    Pre => (M >= 0),
    Post => (M + N = M'Old + N'Old and M < 0);
   


