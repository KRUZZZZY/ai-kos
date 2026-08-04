pragma SPARK_MODE;

with Example; use Example;
with SPARK.Text_IO; use SPARK.Text_IO;

procedure Main
  with Global => (In_Out => (Standard_Output),
                  Output => (Glob));



