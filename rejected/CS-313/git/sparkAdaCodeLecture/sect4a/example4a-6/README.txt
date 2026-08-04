gnatprove -P main.gpr --mode=flow
and as well
gnatprove -P main.gpr --proof=progressive

both return

example.ads:6:24: warning: unused initial value of "X"
    6 |   procedure Exchange (X, Y  : in out Float);
      |                       ^ here

this is the expected error discussed in the lecture
