gnatmake example.adb
  succeeds with no errors
gnatprove -P main.gpr --mode=flow

returns

example.ads:6:30: warning: unused initial value of "X"
    6 |   procedure Wrong_Exchange (X, Y  : in out Float);
      |                             ^ here

this is the expected error discussed in the lecture
