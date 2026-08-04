pragma SPARK_Mode (On);
with AS_IO_Wrapper;  use AS_IO_Wrapper;		
     
	
package body examplepackage is	
	     
		
   procedure example is		
      n : integer;	  
   begin  
      AS_Get(n,"Please type in an integer");		
      as_put(n);	   
   end example;
   
end examplepackage;


