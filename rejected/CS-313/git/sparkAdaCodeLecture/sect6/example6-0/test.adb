Pragma SPARK_Mode;

procedure Test(X : in out Integer) is
begin
   if X > 4
   then X := X + 1;
   else X := X + 2;
   end if;
   pragma Assert_And_Cut (X > 1);   
   if X > 4
   then X := X + 1;
   else X := X + 2;
   end if;
   pragma Assert_And_Cut (X > 2);      
   if X > 4
   then X := X + 1;
   else X := X + 2;
   end if;
end Test;
