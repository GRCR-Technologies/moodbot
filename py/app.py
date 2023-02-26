#!/usr/bin/python3

# importing tkinter for gui
import tkinter as tk
from tkinter.ttk import Label
import time
 
# creating window
window = tk.Tk()
 
# setting attribute
#Owindow.attributes('-fullscreen', True)
window.title("Moodbot v0.1.0")
window.geometry("800x480") 
window.configure(bg='black')
# creating text label to display on window screen 
#w = '480'
#h = '480'

#my_label.config(text = my_text)
class App:
    def __init__(self, window):

        self.window = window
        self.cnt = 0
        self.cnt_sts = False
        self.timer = Label(self.window, text="00:00", font=("Arial", 96), foreground="white", relief="solid", background="black")
        self.msg = Label(self.window, text=" Noskenējiet karti!", font=("Arial", 72), foreground="white", relief="solid", background="black")
        self.msg.place(x=10, y=200)
        self.bat = Label(self.window, text="100%", font=("Arial", 48), foreground="white", relief="solid", background="black")
        self.bat.place(x=630,)

    def mission_complete(self):
        self.msg.config(text="  Misija pabeigta!")
        self.window.after(3000, self.waiting_msg)

    def waiting_msg(self):
        self.msg.config(text=" Noskenējiet karti!")

    def start_countdown(self):
        if self.cnt_sts:
            return
        self.msg.place_forget()
        self.timer.place(x=240, y=200)
        self.cnt = 120
        self.cnt_sts = True
        self.window.after(1000, self.countdown)

    def countdown(self):
        self.timer.config(text=f'{int((self.cnt-(self.cnt%60))/60):02d}:{self.cnt%60:02d}')
        self.cnt -= 1

        if self.cnt < 0:
            self.cnt_sts = False
            self.timer.place_forget()
            self.msg.place(x=10, y=200)
            self.mission_complete()
        else:
            self.window.after(100, self.countdown)


app = App(window)
window.after(2000, app.start_countdown)
window.mainloop()