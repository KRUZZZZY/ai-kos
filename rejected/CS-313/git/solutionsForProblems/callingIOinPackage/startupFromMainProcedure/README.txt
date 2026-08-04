This is an example showing how to deal with IO in a package.
Important points:

* main.adb contains the lines
   AS_Init_Standard_Input;
   AS_Init_Standard_Output;
  to access these procedures it requires
     with AS_IO_Wrapper;  use AS_IO_Wrapper;
  The effect of these procedures is that they intialise
  standard_input, standard_output.

* Because main.adb initialises standard_input, standard_output,
  it has aspect
     Global => (Output=> (Standard_Output, Standard_Input));
  Since Standard_Output, Standard_Input are defined in SPARK-text-io.ads
  it requires
    with SPARK.Text_IO;
    use  SPARK.Text_IO;

* the procedure
    example
  in examplepackage.adb makes use of as_get, as_put
  therefore it requires that
     standard_input, standard_output,
  are initialised

  Therefore example can only be called, after
     standard_input, standard_output,
  have been initialised, therefore
  example is called in main
  after as_init_standard_input, as_init_standard_output

* Since example in examplepackage changes
        standard_input and standard_output we have
  in example.ads
     Global => (In_Out => (Standard_Output, Standard_Input)),
  if changed, Standard_output always depends on Standard_output
              Standard_input always depends on Standard_input
   they depend as well on any other variables their input/output depends on
   In this example standard_output depends as well on standard_input
   since we output variable n, which is obtained as input from as_get(n)
   i.e. it depends on standard_input.
   therefore we have
       Depends => (Standard_Output => (Standard_Output,Standard_Input),
                   Standard_Input  => Standard_Input);
