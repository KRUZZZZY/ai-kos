gnatmake main.adb 
succeeds

Although we have spark_mode(off)
the command
gnatprove -P main.gpr --proof=per_path
gives an error
main.adb:17:07: warning: actuals for this call may be in wrong order [-gnatw.p]

It is referring to the statement
Exchange(Y,X);      
it spots that the variables have the same names but are used in different order.
If one replaces X,Y by A,B the problem disappears.

in addition it reports
main.adb:17:07: warning: actuals for this call may be in wrong order [-gnatw.p]

Checkeing with
gnatprove -P mainWithoutRangeCheck.gpr --proof=per_path
only gives warning

warning: no bodies have been analyzed by GNATprove
