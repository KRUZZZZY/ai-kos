Pragma SPARK_Mode;

-- data flow error regarding Z : in out Integer
-- see README.txt
procedure Exchange_And_Count(X,Y,Z : in out Integer)
  -- 3 information flow errors 
  -- see README.txt
  with Depends => (X => Y,
                   Y => X,
                   Z => Z);
   


