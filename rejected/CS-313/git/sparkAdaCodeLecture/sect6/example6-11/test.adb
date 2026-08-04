Pragma SPARK_Mode;

function Test(X : Integer) return Integer is
begin
   if X = 0
   then return -1;
   else return X + 1;
   end if;
end Test;
