pragma SPARK_Mode;


package Clock is
   
   type Hour is new Integer range 0 .. 23;
   
   type Hour12 is new Integer range 0 .. 11;
   
   function To12 (T : Hour) return Hour12;
     
     
   procedure To12Proc(T : in Hour; U : out Hour12); 
     
end Clock;
     
     
   
     
   
