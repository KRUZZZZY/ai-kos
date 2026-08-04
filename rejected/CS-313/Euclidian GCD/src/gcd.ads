pragma Spark_Mode (On);

package GCD with SPARK_Mode is

   procedure Euclid
     (A  : in  Integer;
      B  : in  Integer;
      G  : out Integer;
      Ga : out Integer;
      Gb : out Integer)
     with
       Pre  => A > 0 and B > 0,
       Post => A = Ga * G and B = Gb * G;

end GCD;
