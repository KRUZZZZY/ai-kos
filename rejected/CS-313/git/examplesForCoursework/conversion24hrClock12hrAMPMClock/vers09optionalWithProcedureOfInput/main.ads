pragma SPARK_Mode (On);	
       		  	
-- The lines				
--   
--     with SPARK.Text_IO; use SPARK.Text_IO;   
-- 
-- Global => (Output => (Standard_Input, Standard_Output));			
--  Depends => (Standard_Input => Null,	
--              Standard_Output => Null);	  			
--   
-- were not in the original version of this example and are not required	
-- in CSCM13/CSC313 2023-24
      	  			
with SPARK.Text_IO; use SPARK.Text_IO;
		  

procedure Main with	
  Global => (Output => (Standard_Input, Standard_Output)),	
  Depends => (Standard_Input => Null,	
              Standard_Output => Null);	  			


