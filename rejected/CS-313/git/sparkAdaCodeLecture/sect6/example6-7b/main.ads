pragma SPARK_Mode;

procedure Main (N : in Integer; I, Res : out Integer) with
  Depends => (I => N, Res => N),
  Pre  => (N in 1 .. 1000),
  Post => (Res = 2 * I and N <= Res and Res < N + 2);
