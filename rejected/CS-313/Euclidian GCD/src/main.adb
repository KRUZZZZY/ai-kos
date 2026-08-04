pragma Spark_Mode (On);

with GCD;
with Spark.Text_IO;
with Spark.Text_IO.Integer_IO;

procedure Main is

   package IO renames Spark.Text_IO;
   package Int_IO is new Spark.Text_IO.Integer_IO (Integer);

   A  : Integer;
   B  : Integer;
   G  : Integer;
   Ga : Integer;
   Gb : Integer;

   Continue : Character := 'Y';

begin
   while Continue = 'Y' or else Continue = 'y' loop

      IO.Put ("Enter a (> 0): ");
      Int_IO.Get (A);

      IO.Put ("Enter b (> 0): ");
      Int_IO.Get (B);

      GCD.Euclid (A, B, G, Ga, Gb);

      IO.Put ("gcd = ");
      Int_IO.Put (G);
      IO.New_Line;

      IO.Put ("ga = ");
      Int_IO.Put (Ga);
      IO.New_Line;

      IO.Put ("gb = ");
      Int_IO.Put (Gb);
      IO.New_Line;

      IO.Put ("Continue? (Y/N): ");
      IO.Get (Continue);
      IO.New_Line;

   end loop;

end Main;
