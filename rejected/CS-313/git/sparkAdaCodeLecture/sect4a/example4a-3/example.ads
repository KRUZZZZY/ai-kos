package Example 
with SPARK_MODE
is
   -- gnatprove -P main.gpr --mode=flow
   -- returns error
   -- example.ads:7:34: medium: "Y" might not be initialized in "A1"
   procedure A1 (X : in Integer; Y : out Integer);
   
   
end Example;
  
  

