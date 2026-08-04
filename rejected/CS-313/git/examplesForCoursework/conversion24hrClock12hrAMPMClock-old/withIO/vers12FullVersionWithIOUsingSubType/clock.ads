pragma SPARK_Mode;


package Clock is
   
   subtype Hour is Integer range 0 .. 23;
   
   subtype Hour12 is Integer range 0 .. 11;
   
   function To12 (T : Hour) return Hour12 with
     Post => (T = To12'Result or  T = To12'Result + 12);
     
     
   procedure To12Proc(T : in Hour; U : out Hour12) with
       Depends => (U => T),
       Post    => (T = U  or T = U + 12);
     
       end Clock;
     
     
   
     
   
