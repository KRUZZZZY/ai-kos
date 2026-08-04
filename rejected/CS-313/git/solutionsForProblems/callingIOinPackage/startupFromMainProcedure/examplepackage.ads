pragma SPARK_Mode (On);

with SPARK.Text_IO;use  SPARK.Text_IO;
     
package examplepackage is		
		       
   procedure example with		
     Global => (In_Out => (Standard_Output, Standard_Input)),	
     Depends => (Standard_Output => (Standard_Output,Standard_Input),
                 Standard_Input  => Standard_Input);
end examplepackage;
   	  	  
		 

