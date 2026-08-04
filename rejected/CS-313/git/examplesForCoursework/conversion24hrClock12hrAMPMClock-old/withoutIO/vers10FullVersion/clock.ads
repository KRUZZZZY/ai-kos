pragma SPARK_Mode;


package Clock is
   
   type Hour is new Integer range 0 .. 23;
   
   type Hour12 is new Integer range 0 .. 11;
   
   function To12 (T : Hour) return Hour12 with
     Post => (T = Hour(To12'Result)  or  T = Hour(To12'Result + 12));
     
     
   procedure To12Proc(T : in Hour; U : out Hour12) with
       Depends => (U => T),
       Post    => (T = Hour(U)  or T = Hour(U) + 12);
     
       end Clock;
     
     
   
     
   
