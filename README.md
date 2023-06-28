# nidaq awg

Use NI output DAQ as an Arbitrary Waveform Generator. 
This module opens a tkinter window in which the user can choose two output channels which can send different signals. 
Furthermore, the user is able to choose the amount of waveforms to send or to just send the waveform continuously untill the user stops it. 
This program uses the nidaqwriter.py file  to communicate with the output DAQ.

## dependencies
This gui needs the follwing imports:
* numpy
* matplotlib
* scipy
* nidaqmx
