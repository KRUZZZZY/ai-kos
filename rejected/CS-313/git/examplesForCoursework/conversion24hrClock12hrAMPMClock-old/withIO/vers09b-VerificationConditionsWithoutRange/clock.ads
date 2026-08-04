pragma SPARK_Mode;



package Clock is
   
--   type Hour is new Integer range 0 .. 23;
   
--   type Hour12 is new Integer range 0 .. 11;
   
   function To12 (T : Integer) return Integer with
     Post => (T = To12'Result  or  T = To12'Result + 12);
     
     
   procedure To12Proc(T : in Integer; U : out Integer) with
       Depends => (U => T),
       Post    => (T = U  or T = U + 12);
     
       end Clock;
     
     
   
     
   
