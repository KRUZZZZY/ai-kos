pragma SPARK_Mode;

package GCD_Verified_Contracts with SPARK_Mode is
   procedure Euclid_GCD_Verified
     (A  : in  Positive;
      B  : in  Positive;
      G  : out Positive;
      GA : out Integer;
      GB : out Integer)
   with
     Depends => ((G, GA, GB) => (A, B)),
     Post =>
       (Integer(A) = Integer(G) * GA
        and Integer(B) = Integer(G) * GB);
end GCD_Verified_Contracts;
