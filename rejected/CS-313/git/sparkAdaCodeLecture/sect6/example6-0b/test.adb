Pragma SPARK_Mode;

procedure Test(X : in out Integer) is
begin
   if X > 4
   then X := X + 1;
   else X := X + 2;
   end if;
if X > 4
   then X := X + 1;
   else X := X + 2;
   end if;
if X > 4
   then X := X + 1;
   else X := X + 2;
   end if;
end Test;
