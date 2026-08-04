gnatmake example.adb
 succeeds with no errors

gnatprove -P main.gpr --mode=flow

returns

example.adb:6:09: warning: variable "T" is assigned but never read [-gnatwm]
    6 |        T : Float;
      |        ^ here

example.adb:10:09: warning: possibly useless assignment to "T", value might not be referenced [-gnatwm]
   10 |        T := X; X:= Y; Y := X;
      |        ^ here

example.adb:10:11: warning: unused assignment
   10 |        T := X; X:= Y; Y := X;
      |        ~~^~~~

example.ads:5:30: warning: unused initial value of "X"
    5 |   procedure Wrong_Exchange (X, Y  : in out Float);
      |                             ^ here

These are the expected error messages from the lecture
