gnatmake example2c1.adb
  succeedsn

gnatprove -P main.gpr --mode=flow
and 
gnatprove -P main.gpr --proof=progressive
both fail:
example2c1.ads:7:13: error: function with output global "Z" is not allowed in SPARK

This is correct, it demonstrates that function F(X) having side effect 
  is not allowed.
