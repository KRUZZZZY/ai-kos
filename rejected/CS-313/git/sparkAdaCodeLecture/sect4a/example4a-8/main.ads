pragma SPARK_MODE;

with Example; use Example;
with SPARK.Text_IO; use SPARK.Text_IO;

package Main 
is

   procedure A1  with   Global => (Output => AbsGlob,
                                   In_Out =>  Standard_Output);
end Main;



