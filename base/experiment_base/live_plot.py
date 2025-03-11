# -*- coding: utf-8 -*-
"""
Created on Mon Apr 15 17:14:06 2024

@author: zerui
"""

import sys, time
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QFont
import Pyro4
from zq_utility import *

def get_relative_time(time0):
    return time.time() - time0

def get_rand():
    return np.random.rand(1)[0]


class PlotWindow(QtWidgets.QMainWindow):
    def __init__(self, title, xlabel, ylabel):
        super().__init__()

        self.xdata = []
        self.ydata = []
        self.closed = False

        self.plot_graph = pg.PlotWidget()
        self.setCentralWidget(self.plot_graph)
        self.setGeometry(200, 100, 640, 480)
        self.plot_graph.setBackground((0, 0, 0))
        self.plot_graph.setTitle(title, color = (246, 241, 238), size = "20pt", bold = True)
        styles = {"color": "red", "font-size": "16pt"}
        self.plot_graph.setLabel("left", ylabel, **styles)
        self.plot_graph.setLabel("bottom", xlabel, **styles)  
        self.plot_graph.showGrid(x=True, y=True)


        # Get X and Y AxisItems
        x_axis = self.plot_graph.getAxis('bottom')
        y_axis = self.plot_graph.getAxis('left')

        # Set font size for X and Y axis ticks
        font = QFont()
        font.setPointSize(12)  # Set desired font size
        font.setBold(False)
        for axis in [x_axis, y_axis]:
            axis.setTickFont(font)
            axis.setTickPen((246, 241, 238))
            axis.setTextPen((246, 241, 238))
            axis.setPen(color=(246, 241, 238), width=2)

        pen = pg.mkPen((160, 32, 240), width=1, style=QtCore.Qt.SolidLine)
        
        # time = np.arange(100)
        # temperature = np.sin(time/3.14)
        # self.plot_graph.addLegend() # provide name for each line that is plotted
        self.line = self.plot_graph.plot(self.xdata, self.ydata, pen = pen,
                             symbol="o",
                             symbolSize=3,
                             symbolBrush=(160, 32, 240))
        
    def update_xy(self, xnew, ynew):
        # self.xdata = self.xdata[1:]
        self.xdata.append(xnew)
        # self.ydata = self.ydata[1:]
        self.ydata.append(ynew)
        
    def update_plot(self):
        self.line.setData(self.xdata, self.ydata)
            
    def closeEvent(self, *args, **kwargs):
        super(QtWidgets.QMainWindow, self).closeEvent(*args, **kwargs)
        self.closed = True

import threading


class MultiPlotter(object):
    """
    This is not the best way to implement threading in Qt.
    Must call close() before the program exits.
    
    Scratch all this.
    It's just much easier to make all plots inside one server and access
    that with the measurement script
    
    """
    def __init__(self):
        self._plot_windows = {}
        # self._qapps = []        
        # tQt = threading.Thread(target=self._qapp.exec, args=())
        # tQt.start()
        # self.tQt = threading.Thread(target=self.main_loop, args=(), daemon = False)
        # self.tQt.start()
        
    def initialize(self):
        self._qapp =  QtWidgets.QApplication([])
        self._running = True
        
    def main_loop(self):
        while(self._running):
            self.update_all_plots()
            time.sleep(0.1)
            for window in self._plot_windows.values():
                if window.closed:
                    self.stop()
        
    def process(self):
        # [qapp.processEvents() for qapp in self._qapps]
        self._qapp.processEvents() 

    # def update_plot(self, plot_label):
    #     if not plot_label in self._plot_windows.keys():
    #         print('Error: no such plot - {}'.format(plot_label))
    #     self._plot_windows[plot_label].update_plot()
    #     self.process()
    def update_all_plots(self):
        for pwindow in self._plot_windows.values():
            pwindow.update_plot()
        self.process()            
    def add_plot(self, plot_label, plot_window : PlotWindow):
        if not plot_label in self._plot_windows.keys():
            # self._qapps.append( QtWidgets.QApplication([]))
            self._plot_windows[plot_label] = plot_window
            self._plot_windows[plot_label].show()
        else:
            print('Error: plot labeled {} already exists'.format(plot_label))

    def close(self):
        # [qapp.exec() for qapp in self._qapps]
        # self.tQt.stop()
        # self._running = False
        self._qapp.exec()
        
    def stop(self):
        self._running = False     

def test_live_plots(mp):
    """
    
    Test function that initializes a MultiplePlotter instance and adds a couple
    of dummy plots in it. 
    The proper way to use this function is to initiate a thread with it.
    """
    # mp = MultiPlotter()
    mp.initialize()
    plabel = "Time vs Rand"
    pwindow = PlotWindow("Time series", "Time (s)", "Val")
    mp.add_plot(plabel, pwindow)
    # print("Added plot")
    mp.add_plot(plabel + ' 2', PlotWindow("Time series", "Time (s)", "Val"))
    mp.main_loop()

if __name__ == '__main__':
    mp = MultiPlotter()
    plabel = "Time vs Rand"
    pwindow = PlotWindow("Time series", "Time (s)", "Val")
    # mp.add_plot(plabel, pwindow)
    # mp.add_plot(plabel + ' 2', pwindow)
    tQt = threading.Thread(target=test_live_plots, args=([mp]), daemon = True)
    tQt.start()
    
    time0 = time.time()
    old_time = 0
    import tqdm
    for i in tqdm.tqdm(np.arange(50)):
        time.sleep(0.5)
        new_time = time.time() - time0
        # pwindow.update_xy(new_time - time0 , new_time - old_time)
        # pwindow.update_plot()
        mp._plot_windows[plabel].update_xy(new_time - time0 , new_time - old_time)
        mp._plot_windows[plabel + ' 2'].update_xy(new_time - time0 , new_time - old_time)
        # mp.update_all_plots()
        # mp.update_plot(plabel)
        old_time = time.time() - time0
    # mp.main_loop()
    mp.close()
    # tQt.join()