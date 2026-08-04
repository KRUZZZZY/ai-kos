This is an example which can be used as a template for the first question
of the coursework.
 It converts numbers in the range from 0 .. 23 to numbers in the range 0 .. 11
   by subtracting 12 if the number is >= 12.
  Note that this is not a completely in accordance with how the conversion
  from 0 .. 23 hours to hours with am/pm works:
   - to be more realistic
        0 should be become 12
        times t in 1 .. 12 should stay
        times t in 13 .. 23 should become t - 12
   - and there is a special treatment of noon and midnight.
 We keep it as it is so that the example stays easy, since the focus is on 
   learning SPARK Ada using an example with simple code.
 We leave it to the reader to adapt this example to a more realistic ones.

The file
   Overview.txt
explains the different versions.







