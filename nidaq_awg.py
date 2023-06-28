""" nidaq_awg.py
Use NI output DAQ as an Arbitrary Waveform Generator. This module opens 
a tkinter window in which the user can choose two output channels which
can send different signals. Furthermore, the user is able to choose the
amount of waveforms to send or to just send the waveform continuously
untill the user stops it. This program uses the nidaqwriter.py file 
to comminucate with the output DAQ.
"""


import time
import tkinter as tk
from tkinter import ttk

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy import signal
import nidaqmx
from nidaqmx import stream_writers

from nidaqwriter import Writer
from entrywidget import Entrywidget


__author__ = "Jaimy Plugge"


FONT = (44)


def constructdcramp(samplerate, ramptime, dctime, amplitude, offset):
    """
    This function is implemented in this program because 
    it is a certain thing that I needed for one of my 
    experiments. It takes the amplitude and sends it for
    <dctime> seconds. Before this constant voltage is set, 
    the voltage will be ramped up via a sine function and 
    also ramped down afterwards. The offset is for how many
    seconds zero voltage should be send before the ramping.
    """
    time_axis = np.arange(0, offset+dctime+(2*ramptime), 1/samplerate)
    #ramp = .5*(1+np.sin(np.arange(-.5*np.pi, .5*np.pi, np.pi
    #                                                   / (ramptime*samplerate))))
    ramp = 1/(ramptime)*np.arange(0,ramptime,1/(samplerate))
    arb = amplitude * np.hstack((np.zeros(int(offset*samplerate)),
                                 ramp,
                                 np.ones(int(dctime*samplerate)),
                                 np.flip(ramp)))
    return time_axis, arb


def returnfinite(x, waveformtype, freq):
    """
    I use this method to return exactly one full pulse
    of a certain waveform type to use for the send finite
    pulses function. This proved to be easier to use than
    the waveforms that are already made in the Mainwindow
    class.
    """
    if waveformtype == "Sine":
        y = np.sin(2*np.pi*freq*x)
    elif waveformtype == "Block":
        y = signal.square(2*np.pi*freq*x)
    elif waveformtype == "Triangle":
        y = signal.sawtooth(2*np.pi*freq*x, width=0.5)
    elif waveformtype == "Saw":
        y = signal.sawtooth(2*np.pi*freq*x)
    else:
        print("No waveform is chosen")
        y = np.zeros(len(x))
    return y


class Choosechannelwindow:
    """
    This is the window that will open on top of the main
    window to selsct the DAQ and channels that will be
    used for the output.
    """
    def __init__(self, mainwindow, channel1var, channel2var):
        self.window = tk.Toplevel(mainwindow)

        self.window.title('Init Window')
        self.window.grab_set()
        self.window.lift(aboveThis=mainwindow)

        system = nidaqmx.system.System.local()
        channellist = [""]
        try:
            for device in system.devices:
                for channel in device.ao_physical_chans:
                    channellist.append(channel.name)
        except:
            tk.messagebox.showerror(
                'DAQ error', 
                'Error: Could not find a DAQ connected to your device.')

        channel1lbl = tk.Label(master=self.window, text="Channel 1:", font=FONT)
        channel2lbl = tk.Label(master=self.window, text="Channel 2:", font=FONT)

        channel1lbl.grid(row=0,column=0)
        channel2lbl.grid(row=1,column=0)

        self.channel1var_ccw = channel1var
        self.channel2var_ccw = channel2var

        channel1 = ttk.Combobox(self.window, values = channellist, 
                                textvariable=self.channel1var_ccw, font=FONT)
        channel1.set(channel1var.get())
        channel1['state'] = 'readonly'
        channel1.grid(row=0,column=1)

        channel2 = ttk.Combobox(self.window, values = channellist, 
                                textvariable=self.channel2var_ccw, font=FONT)
        channel2.set(channel2var.get())
        channel2['state'] = 'readonly'
        channel2.grid(row=1,column=1)

        submitbtn = tk.Button(master=self.window, text='Submit', 
                              command=self.submit, font=FONT)
        submitbtn.grid(row=2,column=0,columnspan=2,sticky="nsew")

    def submit(self):
        self.window.destroy()

    def returnvalues(self):
        return self.channel1var_ccw, self.channel2var_ccw


class Mainwindow:
    def __init__(self):
        self.mainwindow = tk.Tk()
        self.mainwindow.title('Main Window')

        # Make sure the DAQ output gets stopped after the window
        # is closed.
        self.mainwindow.protocol("WM_DELETE_WINDOW", self.quit_me)

        # UI Settings
        self.entrywidth = 10
        self.xpadding = (5, 5)
        self.ypadding = (5, 5)
        self.relief = tk.RIDGE

        # Configure window
        self.mainwindow.rowconfigure([0, 1, 2], weight=1)
        self.mainwindow.columnconfigure([0, 1], minsize=100, weight=1)

        # Make user interface
        self.channel1var = tk.StringVar()
        self.channel2var = tk.StringVar()
        self.createmenu()
        self.createsystemsettings()
        self.waveformvars = [tk.StringVar(),tk.StringVar()]
        self.entrylist1 = []
        self.createchanneloptions("Channel 1",0,2,2,0,self.entrylist1,"blue")
        self.entrylist2 = []
        self.createchanneloptions("Channel 2",0,4,2,1,self.entrylist2,"orange")
        self.extrasettings(0,6,2)
        self.outputoptions(1,6,2,7)


        # Plot things
        self.plotframelabel = ttk.Label(text="Plot Window", font=FONT, 
                                        foreground="black")
        self.plotframe = ttk.LabelFrame(self.mainwindow, 
                                        labelwidget=self.plotframelabel, 
                                        relief=self.relief)
        self.plotframe.grid(row=1, column=0, columnspan=6, rowspan=7, 
                            padx=self.xpadding, pady=self.ypadding, 
                            sticky="nsew")

        self.time_axis = np.linspace(0,1,100000)
        self.waveformmatrix = np.zeros((5, len(self.time_axis)), dtype=float)
        self.waveformmatrix[0,:] = np.zeros(len(self.time_axis))                
        self.waveformmatrix[1,:] = np.sin(2*np.pi*self.time_axis)                       
        self.waveformmatrix[2,:] = signal.square(2*np.pi*self.time_axis)                
        self.waveformmatrix[3,:] = signal.sawtooth(2*np.pi*self.time_axis, width=0.5)  
        self.waveformmatrix[4,:] = signal.sawtooth(2*np.pi*self.time_axis)              

        self.multichan = False


        self.waveformdict = {"Constant": 0,
                             "Sine": 1,
                             "Block": 2,
                             "Triangle": 3,
                             "Saw": 4}


        self.fig, self.axs = plt.subplots()
        self.axs.scatter(self.time_axis,self.waveformmatrix[0,:], s = 0.3)
        self.axs.scatter(self.time_axis,self.waveformmatrix[0,:], s = 0.3)
        self.axs.set_xlabel('Time [s]')
        self.axs.set_ylabel('Amplitude [V]')
        self.legend = self.fig.legend(["No output chosen for channel 1", 
                                       "No output chosen for channel 2"])
        self.legend.legendHandles[0]._sizes = [30]
        self.legend.legendHandles[1]._sizes = [30]
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plotframe)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0,column=0,sticky="nsew")

        # Make sure self.daqout is a thing, the writer class will
        # be called once the channels are chosen.
        self.daqout = False

        # Start main loop
        self.mainwindow.mainloop()

    def createmenu(self):
        """
        This function creates the top menu. The default settings 
        option does not work yet!
        """
        menubar = tk.Menu(self.mainwindow)
        windowmenu = tk.Menu(menubar, tearoff=0)
        windowmenu.add_command(label="Set values to default", 
                               command=self.defaultsettings)
        windowmenu.add_separator()
        windowmenu.add_command(label="Exit", command=self.quit_me)
        menubar.add_cascade(label="Window", menu=windowmenu)

        channelmenu = tk.Menu(menubar, tearoff=0)
        channelmenu.add_command(label="Change channels", 
                                command=self.definechannels)
        channelmenu.add_command(label="Add channels", 
                                command=self.definechannels)
        menubar.add_cascade(label="Channels", menu=channelmenu)

        self.mainwindow.config(menu=menubar)

    def definechannels(self):
        """
        Function that opens the choose channel window and starts 
        the daqout writer once the channels are chosen. It also 
        updates the plot legend to show the channelnames chosen.
        """
        initialize = Choosechannelwindow(self.mainwindow, self.channel1var, 
                                         self.channel2var)
        self.mainwindow.wait_window(initialize.window)
        self.channel1var, self.channel2var = initialize.returnvalues()
        if self.channel2var.get() == "":
            self.legend.remove()
            self.legend = self.fig.legend([self.channel1var.get(), 
                                           "No output chosen for channel 2"])
            self.mulitchan = False
            if len(self.channel1var.get()) > 0:
                if self.daqout != False:
                    self.daqout.stopfunc()
                self.daqout = Writer(self.channel1var.get(),
                                     self.channel2var.get(), 10000)
                self.daqout.task.register_done_event(self.callback)
                self.sendbtn.config(state='normal')
                self.sendzerobtn.config(state='normal')
            else:
                self.sendbtn.config(state='disabled')
                self.sendzerobtn.config(state='disabled')
        else:
            self.legend.remove()
            self.legend = self.fig.legend([self.channel1var.get(), 
                                           self.channel2var.get()])
            self.multichan = True
            if self.daqout != False:
                self.daqout.stopfunc()
            self.daqout = Writer(self.channel1var.get(),self.channel2var.get(), 
                                 10000)
            self.daqout.task.register_done_event(self.callback)
            self.sendbtn.config(state='normal')
            self.sendzerobtn.config(state='normal')
        self.legend.legendHandles[0]._sizes = [30]
        self.legend.legendHandles[1]._sizes = [30]
        self.canvas.draw()

    def createsystemsettings(self):
        """
        This function creates the upper left frame which
        contains the sample rate, output mode (continuous or 
        finite) and the amount of pulses to send when finite
        mode is chosen.
        """
        settingsframelabel = ttk.Label(text="System Settings", font=FONT, 
                                       foreground="black")
        settingsframe = ttk.LabelFrame(self.mainwindow, 
                                       labelwidget=settingsframelabel, 
                                       relief=self.relief)
        settingsframe.grid(row=0, column=0, columnspan=2, padx=self.xpadding, 
                           pady=self.ypadding, sticky="nsew")

        samprlabel = tk.Label(master=settingsframe, text="Sample Rate [Hz]: ", 
                              font=FONT)

        minmaxsampr = [1, 1E5]
        self.samprentry = Entrywidget(master=settingsframe, 
                                      width=self.entrywidth, font=FONT, 
                                      minmax=minmaxsampr, 
                                      callfunc=self.plotupdate)
        self.samprentry.insert(0,10000)
        
        samprlabel.grid(row=0, column=0, sticky="e")
        self.samprentry.grid(row=0, column=1, sticky="nsew")


        outputlabel = tk.Label(master=settingsframe, text="Output Type: ", 
                               font=FONT)
        self.outputvar = tk.StringVar()
        outputwavecombo = ttk.Combobox(settingsframe, 
                                       values=("Continuous", "Finite"), 
                                       textvariable=self.outputvar, 
                                       width=self.entrywidth, font=FONT)
        outputwavecombo['state'] = 'readonly'
        outputwavecombo.set("Continuous")

        outputlabel.grid(row=1, column=0, sticky="e")
        outputwavecombo.grid(row=1, column=1, sticky="nsew")

        amountlabel = tk.Label(master=settingsframe, text="Waveform Amount: ", 
                               font=FONT)
        minmaxamount = [1, 1E3]
        self.amountentry = Entrywidget(master=settingsframe, 
                                       width=self.entrywidth, font=FONT, 
                                       minmax=minmaxamount, 
                                       callfunc=self.plotupdate)
        self.amountentry.insert(0,1)
        
        amountlabel.grid(row=2, column=0, sticky="e")
        self.amountentry.grid(row=2, column=1, sticky="nsew")
        self.amountentry.config(state=tk.DISABLED)

        outputwavecombo.bind("<<ComboboxSelected>>", lambda event, 
                             entry=self.amountentry:self.systemsettingsupdate(entry, 
                                                                              event))

    def createchanneloptions(self, title_text, row_nr, column_nr, columnspan, 
                             waveformvar, entrylist, color):
        """
        Create the channel frame which contains the amplitude,
        frequency and offset options for a single channel.
        """
        labeltextlist = ["Amplitude [V]: ", "Frequency [Hz]: ", "Offset [V]: "]
        entrystandard = [1, 1, 0]
        labellist = []

        waveformlist = ["Constant", "Sine", "Block", "Triangle", "Saw"]

        minmaxentries = [[0,10], [0.1,1E4], [-10, 10]]

        framelabel = ttk.Label(text=title_text, font=FONT, foreground=color)
        frame = ttk.LabelFrame(self.mainwindow, labelwidget=framelabel, 
                               relief=self.relief)
        frame.grid(row=row_nr, column=column_nr, columnspan=columnspan, 
                   padx=self.xpadding, pady=self.ypadding, sticky="nsew")

        waveformlabel = tk.Label(master=frame, text="Waveform: ", font=FONT)
        waveformcombo = ttk.Combobox(frame, values=waveformlist, 
                                     textvariable=self.waveformvars[waveformvar], 
                                     width=self.entrywidth, font=FONT)
        waveformcombo['state'] = 'readonly'
        waveformcombo.set("Constant")

        waveformlabel.grid(row=0, column=0, sticky="e")
        waveformcombo.grid(row=0, column=1, sticky="nsew")

        for _ in range(3): 
            label = tk.Label(master=frame, text=labeltextlist[_], font=FONT)
            entry = Entrywidget(master=frame, width=self.entrywidth, font=FONT, 
                                minmax=minmaxentries[_], callfunc=self.plotupdate)
            entry.insert(0,entrystandard[_])

            label.grid(row=_+1, column=0, sticky="e")
            entry.grid(row=_+1, column=1, sticky="nsew")

            if _ < 2:
                entry.config(state=tk.DISABLED)

            labellist.append(label)
            entrylist.append(entry)

        waveformcombo.bind("<<ComboboxSelected>>", 
                           lambda event: self.plotupdate(event))

    def extrasettings(self, row_nr, column_nr, columnspan):
        """
        This function constructs the frame containing the
        settings for the delaytime, which can be used as
        phase delay also in continuous output. Furthermore,
        it contains the ramptime for both channels of the 
        ramped DC function and the total time for both 
        channels.
        """
        extraframelabel = ttk.Label(text="Extra Settings", font=FONT, 
                                    foreground="black")
        extraframe = ttk.LabelFrame(self.mainwindow, labelwidget=extraframelabel, 
                                    relief=self.relief)
        extraframe.grid(row=row_nr, column=column_nr, columnspan=columnspan, 
                        padx=self.xpadding, pady=self.ypadding, sticky="nsew")

        delaylabel = tk.Label(master=extraframe, text="Channel 2 Delay [s]: ", 
                              font=FONT)
        minmaxdelay = [0, 10]
        self.delayentry = Entrywidget(master=extraframe, width=self.entrywidth, 
                                      font=FONT, minmax=minmaxdelay, 
                                      callfunc=self.plotupdate)
        self.delayentry.insert(0,0)

        delaylabel.grid(row=0, column=0, sticky="e")
        self.delayentry.grid(row=0, column=1, sticky="nsew")     

        ramplabel = tk.Label(master=extraframe, text="Ramp Time [s]: ", font=FONT)
        minmaxramp = [0.1, 10]
        self.rampentry = Entrywidget(master=extraframe, width=self.entrywidth, 
                                     font=FONT, minmax=minmaxramp, 
                                     callfunc=self.plotupdate)
        self.rampentry.insert(0,1)

        ramplabel.grid(row=1, column=0, sticky="e")
        self.rampentry.grid(row=1, column=1, sticky="nsew")

        dctime1label = tk.Label(master=extraframe, text="DC Time 1 [s]: ", 
                                font=FONT)
        minmaxdctime1 = [0, 1000]
        self.dctime1entry = Entrywidget(master=extraframe, width=self.entrywidth, 
                                        font=FONT, minmax=minmaxdctime1, 
                                        callfunc=self.plotupdate)
        self.dctime1entry.insert(0,0)

        dctime1label.grid(row=2, column=0, sticky="e")
        self.dctime1entry.grid(row=2, column=1, sticky="nsew") 

        dctime2label = tk.Label(master=extraframe, text="DC Time 2 [s]: ", font=FONT)
        minmaxdctime2 = [0, 20]
        self.dctime2entry = Entrywidget(master=extraframe, width=self.entrywidth, 
                                        font=FONT, minmax=minmaxdctime2, 
                                        callfunc=self.plotupdate)
        self.dctime2entry.insert(0,0)

        dctime2label.grid(row=3, column=0, sticky="e")
        self.dctime2entry.grid(row=3, column=1, sticky="nsew")    

    def outputoptions(self, row_nr, column_nr, columnspan, rowspan):
        """
        This function constructs the right most frame which
        contains the information of the current output and
        the "send output" button. It also has a "set output
        to zero" button for if you want to quickly stop the 
        output.
        """
        outputframelabel = ttk.Label(text="Output", font=FONT, foreground="black")
        outputframe = ttk.LabelFrame(self.mainwindow, 
                                     labelwidget=outputframelabel, 
                                     relief=self.relief)
        outputframe.grid(row=row_nr, column=column_nr, columnspan=columnspan, 
                         rowspan=rowspan, padx=self.xpadding, 
                         pady=self.ypadding, sticky="nsew")

        outputchan1ttl = tk.Label(master=outputframe, 
                                  text="Current output channel 1:", font=FONT)
        outputchan1ttl.grid(row=0, column=0, sticky="w")

        self.outputchan1lbl = tk.Text(master=outputframe, height=4, width=26, 
                                      font=FONT)
        self.outputchan1lbl.grid(row=1, column=0, sticky="w")
        self.outputchan1lbl.insert(tk.END,"Output is off")
        self.outputchan1lbl.configure(state="disabled")

        blankspace = tk.Label(master=outputframe, text="", font=FONT)
        blankspace.grid(row=2, column=0, sticky="w")

        outputchan2ttl = tk.Label(master=outputframe, 
                                  text="Current output channel 2:", font=FONT)
        outputchan2ttl.grid(row=3, column=0, sticky="w")

        self.outputchan2lbl = tk.Text(master=outputframe, height=4, width=26, 
                                      font=FONT)
        self.outputchan2lbl.grid(row=4, column=0, sticky="w")
        self.outputchan2lbl.insert(tk.END,"Output is off")
        self.outputchan2lbl.configure(state="disabled")

        blankspace2 = tk.Label(master=outputframe, text="", font=FONT)
        blankspace2.grid(row=5, column=0, sticky="w")

        self.outputindicator = tk.Label(master=outputframe, 
                                        text="Output is off", fg="Red", 
                                        font=FONT)
        self.outputindicator.grid(row=6, column=0, sticky="nsew")

        blankspace3 = tk.Label(master=outputframe, text="", font=FONT)
        blankspace3.grid(row=7, column=0, sticky="w")

        self.sendbtn = tk.Button(master=outputframe, text='Send', 
                                 command=self.sendsignal, font=FONT)
        self.sendbtn.grid(row=8, column=0, sticky="nsew")
        self.sendbtn.config(state='disabled')

        blankspace4 = tk.Label(master=outputframe, text="", font=FONT)
        blankspace4.grid(row=9, column=0, sticky="w")

        self.sendzerobtn = tk.Button(master=outputframe, text='Turn Output Off', 
                                     command = self.stopoutput, font=FONT)
        self.sendzerobtn.grid(row=10, column=0, sticky="nsew")
        self.sendzerobtn.config(state='disabled')

    def systemsettingsupdate(self, entry, event=None):
        if self.outputvar.get() == "Continuous":
            entry.config(state=tk.DISABLED)
        else:
            entry.config(state=tk.NORMAL)
        self.plotupdate()

    def plotupdate(self, event=None):
        if self.waveformvars[0].get() == "Constant":
            self.entrylist1[0].config(state=tk.DISABLED)    # Amplitude
            self.entrylist1[1].config(state=tk.DISABLED)    # Frequency
        else:
            self.entrylist1[0].config(state=tk.NORMAL)
            self.entrylist1[1].config(state=tk.NORMAL)

        if self.waveformvars[1].get() == "Constant":
            self.entrylist2[0].config(state=tk.DISABLED)
            self.entrylist2[1].config(state=tk.DISABLED)
        else:
            self.entrylist2[0].config(state=tk.NORMAL)
            self.entrylist2[1].config(state=tk.NORMAL)

        self.axs.clear()
        if (self.outputvar.get() == "Finite" and 
                self.waveformvars[0].get() == "Constant" and 
                self.waveformvars[1].get() == "Constant"):
            self.axs.scatter(*constructdcramp(float(self.samprentry.get()), 
                                              float(self.rampentry.get()), 
                                              float(self.dctime1entry.get()), 
                                              float(self.entrylist1[2].get()), 0), 
                                              s=0.3)
            self.axs.scatter(*constructdcramp(float(self.samprentry.get()), 
                                              float(self.rampentry.get()), 
                                              float(self.dctime2entry.get()), 
                                              float(self.entrylist2[2].get()), 
                                              float(self.delayentry.get())), 
                                              s=0.3)
        else:
            waveformvalue1 = self.waveformdict[self.waveformvars[0].get()]
            skiprate1 = (float(self.entrylist1[1].get()) 
                         * len(self.time_axis)
                         / float(self.samprentry.get()))
            ind1 = ((np.arange(len(self.time_axis)) * skiprate1) 
                     % len(self.time_axis)).astype(int)
            xnow1 = self.time_axis*skiprate1 / (float(self.entrylist1[1].get()))
            self.axs.scatter(xnow1,float(self.entrylist1[0].get()) 
                                   * self.waveformmatrix[waveformvalue1,ind1] 
                                   + float(self.entrylist1[2].get()), s = 0.3)

            waveformvalue2 = self.waveformdict[self.waveformvars[1].get()]
            skiprate2 = (float(self.entrylist2[1].get())
                         * len(self.time_axis)
                         / float(self.samprentry.get()))
            ind2 = ((np.arange(len(self.time_axis)) * skiprate2) 
                     % len(self.time_axis)).astype(int)
            xnow2 = self.time_axis*skiprate2 / (float(self.entrylist2[1].get()))
            y2 = (float(self.entrylist2[0].get())
                  * self.waveformmatrix[waveformvalue2,ind2] 
                  + float(self.entrylist2[2].get()))
            self.axs.scatter(xnow2,
                             np.roll(y2,int(float(self.samprentry.get())
                                            * float(self.delayentry.get()))), s=0.3)
            
            if float(self.entrylist1[1].get()) > float(self.entrylist2[1].get()):
                pulselength = 1/float(self.entrylist2[1].get())
            else:
                pulselength = 1/float(self.entrylist1[1].get())
        
            self.axs.set_xlim(0-0.05*pulselength, pulselength+0.05*pulselength)
        self.axs.set_xlabel('Time [s]')
        self.axs.set_ylabel('Amplitude [V]')
        self.canvas.draw()

    def sendsignal(self):
        amp1 = self.entrylist1[0].get()
        freq1 = self.entrylist1[1].get()
        offs1 = self.entrylist1[2].get()
        amp2 = self.entrylist2[0].get()
        freq2 = self.entrylist2[1].get()
        offs2 = self.entrylist2[2].get()
        samplerate = self.samprentry.get()
        if self.waveformvars[0].get() == "Constant":
            txtoutputchannel1 = (f"Waveform:\t\t{self.waveformvars[0].get()}\n"
                                 f"Offset:\t\t{offs1} V")
        else:
            txtoutputchannel1 = (f"Waveform:\t\t{self.waveformvars[0].get()}\n"
                                 f"Amplitude:\t\t{amp1} V\n"
                                 f"Frequency:\t\t{freq1} Hz\n"
                                 f"Offset:\t\t{offs1} V")
        if self.waveformvars[1].get() == "Constant":
            txtoutputchannel2 = (f"Waveform:\t\t{self.waveformvars[1].get()}\n"
                                 f"Offset:\t\t{offs2} V")
        else:
            txtoutputchannel2 = (f"Waveform:\t\t{self.waveformvars[1].get()}\n"
                                 f"Amplitude:\t\t{amp2} V\n"
                                 f"Frequency:\t\t{freq2} Hz\n"
                                 f"Offset:\t\t{offs2} V")
        self.outputchan1lbl.configure(state=tk.NORMAL)
        self.outputchan1lbl.delete(1.0,tk.END)
        self.outputchan1lbl.insert(tk.END,txtoutputchannel1)
        self.outputchan1lbl.configure(state=tk.DISABLED)
        self.outputchan2lbl.configure(state=tk.NORMAL)
        self.outputchan2lbl.delete(1.0,tk.END)
        self.outputchan2lbl.insert(tk.END,txtoutputchannel2)
        self.outputchan2lbl.configure(state=tk.DISABLED)

        self.outputindicator.config(text="Output is on", fg="green")

        if (self.outputvar.get() == "Finite" and 
                self.waveformvars[0].get() == "Constant" and 
                self.waveformvars[1].get() == "Constant"):
            time1, y1 = constructdcramp(float(samplerate), 
                                        float(self.rampentry.get()), 
                                        float(self.dctime1entry.get()), 
                                        float(offs1), 0)
            time2, y2 = constructdcramp(float(samplerate), 
                                        float(self.rampentry.get()), 
                                        float(self.dctime2entry.get()), 
                                        float(offs2), 
                                        float(self.delayentry.get()))
            if len(y2) > len(y1):
                outputsignal = np.vstack((np.hstack((y1, np.zeros(len(y2)-len(y1))))
                                          , y2))
            elif len(y2) < len(y1):
                outputsignal = np.vstack((y1, 
                                          np.hstack((y2, np.zeros(len(y1)-len(y2))))))
            else:
                outputsignal = np.vstack((y1, y2))
        
            self.daqout.pausefunc()
            self.daqout.sample_rate = int(samplerate)
            self.daqout.singleoutput(outputsignal)

        elif self.outputvar.get() == "Finite":
            x1 = np.arange(0, 1/float(freq1), 1/(int(samplerate)))
            y1 = returnfinite(x1, self.waveformvars[0].get(), float(freq1))
            if self.waveformvars[1].get() == "Constant":
                y2 = np.zeros(len(y1), dtype=float)
            x2 = np.arange(0, 1/float(freq2), 1/(int(samplerate)))
            y2 = returnfinite(x2, self.waveformvars[1].get(), float(freq2))
            ynew1 = y1
            ynew2 = y2
            for i in range(int(self.amountentry.get())-1):
                ynew1 = np.hstack((ynew1, y1))
                ynew2 = np.hstack((ynew2, y2))

            ynew1 = np.hstack((ynew1, [0]))
            ynew2 = np.roll(ynew2, int(float(samplerate)
                                       * float(self.delayentry.get())))
            ynew2 = np.hstack((ynew2, [0]))

            outputsignal = np.vstack((ynew1, ynew2))
            self.daqout.pausefunc()
            self.daqout.sample_rate = int(samplerate)
            self.daqout.singleoutput(outputsignal)


        else:
            waveformvalue1 = self.waveformdict[self.waveformvars[0].get()]
            skiprate1 = (float(freq1)*len(self.time_axis)/float(samplerate))
            ind1 = ((np.arange(len(self.time_axis))*skiprate1) 
                     % len(self.time_axis)).astype(int)
            waveformout = (float(amp1)*self.waveformmatrix[waveformvalue1,ind1] 
                           + float(offs1))

            waveformvalue2 = self.waveformdict[self.waveformvars[1].get()]
            skiprate2 = (float(freq2)*len(self.time_axis)/float(samplerate))
            ind2 = ((np.arange(len(self.time_axis))*skiprate2) 
                     % len(self.time_axis)).astype(int)
            waveformout = np.vstack((waveformout, 
                                     np.roll(float(amp2) 
                                     * self.waveformmatrix[waveformvalue2,ind2] 
                                     + float(offs2), 
                                     int(float(samplerate)
                                     * float(self.delayentry.get())))))

            self.daqout.pausefunc()
            self.daqout.sample_rate = int(samplerate)
            self.daqout.outputcontinuously(waveformout)

    def callback(self, task_handle, status, callback_data):
        print(f"Stopped with status {status}")
        self.daqout.task.stop()
        self.outputchan1lbl.configure(state=tk.NORMAL)
        self.outputchan1lbl.delete(1.0,tk.END)
        self.outputchan1lbl.insert(tk.END,"Output is off")
        self.outputchan1lbl.configure(state=tk.DISABLED)
        self.outputchan2lbl.configure(state=tk.NORMAL)
        self.outputchan2lbl.delete(1.0,tk.END)
        self.outputchan2lbl.insert(tk.END,"Output is off")
        self.outputchan2lbl.configure(state=tk.DISABLED)
        self.outputindicator.config(text="Output is off", fg="red")
        return 0

    def defaultsettings(self):
        print("Does not work yet")
       
    def quit_me(self):
        print('Closing the program')
        self.mainwindow.quit()
        self.mainwindow.destroy()
        if self.daqout != False:
            self.daqout.stopfunc()
            print("Stopped DAQ output")

    def stopoutput(self):
        self.daqout.pausefunc()
        self.daqout.outputcontinuously(np.zeros((2, 10), dtype=float))
        self.outputchan1lbl.configure(state=tk.NORMAL)
        self.outputchan1lbl.delete(1.0,tk.END)
        self.outputchan1lbl.insert(tk.END,"Output is off")
        self.outputchan1lbl.configure(state=tk.DISABLED)
        self.outputchan2lbl.configure(state=tk.NORMAL)
        self.outputchan2lbl.delete(1.0,tk.END)
        self.outputchan2lbl.insert(tk.END,"Output is off")
        self.outputchan2lbl.configure(state=tk.DISABLED)
        self.outputindicator.config(text="Output is off", fg="red")

    def helpme(self):
        "I should add this..."


def main():
    Mainwindow()


if __name__ == "__main__":
    main()