""" entrywidget.py
This module contains a class makes use of the tkinter Entry class to add 
functionality to the standard tkinter Entry widget. This includes using 
the arrow keys to increase and decrease the number inside the entry box, 
being able to type "k" for a factor of 1000 and "M" for a million. It 
also checks if the value inside the entry does not exceed the minimum or 
maximum value of that box. 
"""


import tkinter as tk

import numpy as np


__author__ = "Jaimy Plugge"


FONT = (44)


class Entrywidget(tk.Entry):
    def __init__(self, master, width, font, minmax, callfunc):
        super().__init__(master=master, width=width, font=FONT)
        self.minmax = minmax

        self.callfunc = callfunc

        self.bind("<Up>", lambda event: self.up_arrow_input(event))
        self.bind("<Down>", lambda event: self.down_arrow_input(event))
        self.bind("<Return>", lambda event: self.enter_input(event))

    def enter_input(self, event=None):
        number_str = self.get()
        if number_str[-1] == "k":
            number_float = float(number_str[:-1])
            number_str = str(int(number_float*1000))
        elif number_str[-1] == "M":
            number_float = float(number_str[:-1])
            number_str = str(int(number_float*1000000))
        elif number_str[-1] not in "1234567890":
            while number_str[-1] not in "1234567890":
                number_str = number_str[:-1]
        if float(number_str) > self.minmax[1]:
            number_str = int(self.minmax[1])
        elif float(number_str) < self.minmax[0]:
            number_str = self.minmax[0]
        self.delete(0, tk.END)
        self.insert(0, number_str)
        self.callfunc()
            
    def up_arrow_input(self, event=None):
        tkinter_position = self.index(tk.INSERT)
        number_str = self.get()
        decimalindex = number_str.find(".")
        if decimalindex < 0:
            number_int = int(number_str)
            position = len(number_str)-tkinter_position
            new_number = number_int + 10 ** position
            if new_number > self.minmax[1]:
                new_number = number_int
            new_number_str = str(new_number)
            if len(new_number_str) > len(number_str):
                tkinter_position = tkinter_position + 1
        else:
            number_float = float(number_str)
            position = len(number_str)-tkinter_position
            shift = len(number_str)-decimalindex
            if position - shift >= 0:
                new_number = number_float + 10 ** (position-shift)
            elif position - shift < -1:
                new_number = number_float + 10 ** (position-shift+1)
            else:
                new_number = number_float
            if new_number > self.minmax[1]:
                new_number = number_float
            new_number_str = str(round(new_number, shift))
        self.delete(0, tk.END)
        self.insert(0, new_number_str)
        self.icursor(tkinter_position)
        self.callfunc()

    def down_arrow_input(self, event=None):
        tkinter_position = self.index(tk.INSERT)
        number_str = self.get()
        decimalindex = number_str.find(".")
        if decimalindex < 0:
            number_int = int(number_str)
            position = len(number_str)-tkinter_position
            new_number = number_int - 10 ** position
            if new_number < self.minmax[0]:
                new_number = number_int
            new_number_str = str(new_number)
            if len(new_number_str) < len(number_str):
                tkinter_position = tkinter_position - 1
        else:
            number_float = float(number_str)
            position = len(number_str)-tkinter_position
            shift = len(number_str)-decimalindex
            if position - shift >= 0:
                new_number = number_float - 10 ** (position-shift)
            elif position - shift < -1:
                new_number = number_float - 10 ** (position-shift+1)
            else:
                new_number = number_float
            if new_number < self.minmax[0]:
                new_number = number_float
            new_number_str = str(round(new_number, shift))
        self.delete(0, tk.END)
        self.insert(0, new_number_str)
        self.icursor(tkinter_position)
        self.callfunc()


class Mainwindow:
    def __init__(self):
        self.mainwindow = tk.Tk()
        self.mainwindow.title('Main Window')

        self.entry = Entrywidget(master=self.mainwindow, width=10, font=FONT, 
                                 minmax=[0,100000], callfunc=self.printentry)
        self.entry.pack()

        self.btn = tk.Button(master=self.mainwindow, width=10, 
                             command=self.printentry)
        self.btn.pack()

        self.entry.insert(0,10)

        self.mainwindow.mainloop()

    def printentry(self):
        print(self.entry.get())


if __name__ == "__main__":
    Mainwindow()