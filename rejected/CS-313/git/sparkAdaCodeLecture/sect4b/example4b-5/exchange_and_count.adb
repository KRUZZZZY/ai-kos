pragma SPARK_Mode;

procedure Exchange_And_Count(X,Y : in out Integer; Z : out Integer) is
   T : Integer;
begin
   T := X; X:= Y; Y := T; Z := T;
end Exchange_And_Count;

