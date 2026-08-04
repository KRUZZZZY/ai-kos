Pragma SPARK_Mode;

procedure Decrease_Increase(X,Y : in out Integer; Z : in Integer)
  with Depends => (X => (X,Z),
                   Y => (X,Y,Z));
   


