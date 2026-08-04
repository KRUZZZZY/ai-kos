pragma SPARK_Mode;

function Test(X : Integer) return Integer
  with 
    Pre => (X > 0),
    Post => (Test'Result = X + 1);
   

