-- pragma SPARK_MODE;
--      not needed because of line below
--      with SPARK_MODE is     
-- with SPARK.Text_IO; use SPARK.Text_IO;

package body Example 
with SPARK_MODE is   
   
   procedure Test1 (A : Integer)

   is
      type Vec is array(0 .. A) of Integer; 
      B : Vec ; 
   begin
      for I in 0 .. A loop
         B(I):= 3;
      end loop;
      for I in 0 .. 7 loop
         if I = A then
            B(I):= 7; 
            Mainvar:= 3;
         end if;
         -- causes that range check may fail when using 
         --      gnatprove -P main.gpr --mode=prove
         -- no problem when using
         --      gnatprove -P mainWithoutRangeCheck.gpr --mode=prove
         if I = A + 1 then 
            --  sparkada check causes array index check might fail
            B(I):= 3;
            Mainvar:= 7;
         end if;
         --  sparkada check causes array index check might fail      
         if B(I) = 7 then Mainvar:= 4; 
         end if;
      end loop;
   end Test1;

end Example;
