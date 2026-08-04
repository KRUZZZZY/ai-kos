pragma SPARK_Mode (On);
package Loop_Entry is

   procedure Test (A,B: in out Integer)
     with
       Depends => (A => A,
                   B => (A, B)),
       Post => (A + B = A'Old + B'Old);
end Loop_Entry;
