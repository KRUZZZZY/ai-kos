This is an example of a wrong way of reading a digit.
SPARK Ada reports range check might fail in the line
AS_Get(T,"Please type in an integer; please try again");

the program crashes when you run it and the user enters a number
not in range 0 .. 9.

Solution: see sect6/example6-24
