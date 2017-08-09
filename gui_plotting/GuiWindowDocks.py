""" Standard imports """

"""
    Author: Shameer Sathar
    Description: Provide Gui Interface.
"""
import sys
import os
import numpy as np
import platform
import time
import threading
from threading import Thread




from multiprocessing import Process
# Main GUI support

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore, USE_PYSIDE
from pyqtgraph.dockarea import *

# import VideoTemplate_pyside as VideoTemplate
# import VideoTemplate_pyqt as VideoTemplate

from pyqtgraph.widgets.RawImageWidget import RawImageGLWidget, RawImageWidget


# import cPickle as pickle # Python3 
import pickle
import matplotlib as mpl  

mpl.use('TkAgg') # TM EDIT (compatibility for mac)
import matplotlib.pyplot as plt

import scipy.io
import theano

import lasagne
from lasagne import layers
from lasagne.updates import nesterov_momentum

from nolearn.lasagne import NeuralNet
from nolearn.lasagne import visualize

# Locally-developed modules
from TrainingDataPlot import TrainingDataPlot
from file_io.ARFFcsvReader import ARFFcsvReader
from ml_classes.WekaInterface import WekaInterface
from ml_classes.FeatureAnalyser import FeatureAnalyser
from ml_classes.SlowWaveCNN import SlowWaveCNN
import config_global as cg
from file_io.gems_sigpy import *
from signal_processing.preprocessing import preprocess
from signal_processing.mapping import *

from signal_processing.livedata import LiveData


# For debugging purps

class GuiWindowDocks:

    def __init__(self):
        """
        Initialise the properties of the GUI. This part of the code sets the docks, sizes
        :return: NULL
        """

        self.rowNum = 0
        self.app = QtGui.QApplication([])
        self.win = QtGui.QMainWindow()
        area = DockArea()
        self.d_control = Dock("Dock Controls", size=(50, 200))
        self.d_plot = Dock("Dock Plots", size=(500, 200))
        self.d_train = Dock("Training Signal", size=(500, 50))
        area.addDock(self.d_control, 'left')
        area.addDock(self.d_plot, 'right')
        area.addDock(self.d_train, 'bottom', self.d_plot)

        self.win.setWindowTitle("PySig")

        self.win.setCentralWidget(area)
        self.win.resize(1500, 800)
        self.win.setWindowTitle('PySig Training')
        self.add_dock_widgets_controls()
        self.add_menu_bar()

        self.curves_left = []
        self.curves_right = []
        self.curve_bottom = []
        self.add_dock_widgets_plots()
        self.set_crosshair()
        self.set_rect_region_ROI()
        self.elec = []
        self.data = []

        self.set_plot_data(cg.dat['SigPy']['normData'], cg.dat['SigPy']['normData'].shape[0], cg.dat['SigPy']['normData'].shape[1])

        self.trainingDataPlot = TrainingDataPlot()
        
        self.saveBtn_events.clicked.connect(lambda: self.add_as_events())
        self.saveBtn_nonEvents.clicked.connect(lambda: self.add_non_events())
        self.undoBtn.clicked.connect(lambda: self.undo())
        self.writeWEKABtn.clicked.connect(lambda: self.writeWEKA_data())
        self.readPredictedVal.clicked.connect(lambda: self.read_predicted())

        self.amplitudeMapping.clicked.connect(lambda: self.plot_amplitude_map())        
        self.analyseInternal.clicked.connect(lambda: self.analyse_internal())
        self.btnViewLiveData.clicked.connect(lambda: self.view_live_data())

        self.save_trained_data.clicked.connect(lambda: self.save_trained())
        self.load_trained_data.clicked.connect(lambda: self.load_trained())

        self.win.showMaximized()
        self.win.show()



    def add_one(self):
        self.rowNum+=1
        return self.rowNum



    def add_menu_bar(self):

        ## MENU BAR
        self.statBar = self.win.statusBar()

        self.mainMenu = self.win.menuBar()
        self.fileMenu = self.mainMenu.addMenu('&File')

        ## Load file
        self.loadAction = QtGui.QAction('&Load GEMS .mat', self.fileMenu)        
        self.loadAction.setShortcut('Ctrl+L')
        self.loadAction.setStatusTip('')
        self.loadAction.triggered.connect(lambda: self.load_file_selector__gui_set_data())

        self.fileMenu.addAction(self.loadAction)


        ## Save as gems file 
        self.saveAsAction = QtGui.QAction('&Save as GEMS .mat', self.fileMenu)        
        self.saveAsAction.setStatusTip('Save data with filename.')
        self.saveAsAction.triggered.connect(lambda: self.save_as_file_selector())

        self.fileMenu.addAction(self.saveAsAction)


        ## Save (update existing file)
        self.saveAction = QtGui.QAction('&Save', self.fileMenu)
        self.saveAction.setShortcut('Ctrl+S')
        self.saveAction.setStatusTip('Overwrite currently loaded file.')
        self.saveAction.triggered.connect(lambda: self.save_file_selector())

        self.fileMenu.addAction(self.saveAction)    

        ## Exit 
        self.quitAction = QtGui.QAction('Close', self.fileMenu)        
        self.quitAction.setStatusTip('Quit the program')
        self.quitAction.setShortcut('Ctrl+Q')
        self.quitAction.triggered.connect(lambda: self.exit_app())

        self.fileMenu.addAction(self.quitAction)



    def add_dock_widgets_controls(self):
        w1l = QtGui.QVBoxLayout()

        w1 = pg.LayoutWidget()
        label = QtGui.QLabel('Usage info')
        label.setAlignment(QtCore.Qt.AlignTop)

        self.saveBtn_events = QtGui.QPushButton('Save As Events')
        self.saveBtn_nonEvents = QtGui.QPushButton('Save As Non-Events')
        self.undoBtn = QtGui.QPushButton('Undo')
        self.writeWEKABtn = QtGui.QPushButton('Write WEKA')
        self.readPredictedVal = QtGui.QPushButton('Read Weka CSV')
        self.analyseInternal = QtGui.QPushButton('Analyse Events')
        self.amplitudeMapping = QtGui.QPushButton('Amplitude and Event Mapping')
        self.btnViewLiveData = QtGui.QPushButton('Live Mapping')

        self.save_trained_data = QtGui.QPushButton('Save Training')
        self.load_trained_data = QtGui.QPushButton('Load Training')

        # self.dataTypeLayout=QtGui.QHBoxLayout()  # layout for the central widget
        # self.dataTypeWidget=QtGui.QWidget(self)  # central widget
        # self.dataTypeWidget.setLayout(self.dataTypeLayout)

        # Control for toggling type of data whether pacing or normal
        dataTypeLabel = QtGui.QLabel('Physiology:')
        dataTypeLabel.setAlignment(QtCore.Qt.AlignBottom)


        self.dataType=QtGui.QButtonGroup() 

        self.btnPacing = QtGui.QRadioButton('Pacing')
        self.btnIsNormal = QtGui.QRadioButton('Normal')
        self.btnIsNormal.setChecked(1);

        self.dataType.addButton(self.btnPacing, 0)
        self.dataType.addButton(self.btnIsNormal, 1)
        self.dataType.setExclusive(True)

        # Control for toggling whether to capture live data
        liveDataLabel = QtGui.QLabel('Data capture:')
        liveDataLabel.setAlignment(QtCore.Qt.AlignBottom)



        w1.addWidget(label, row=self.add_one(), col=0)
        # w1.addWidget(self.loadRawData, row=self.add_one(), col=0)

        w1.addWidget(self.saveBtn_events, row=self.add_one(), col=0)
        w1.addWidget(self.saveBtn_nonEvents, row=self.add_one(), col=0)
        w1.addWidget(self.undoBtn, row=self.add_one(), col=0)
        w1.addWidget(self.writeWEKABtn, row=self.add_one(), col=0)
        w1.addWidget(self.readPredictedVal, row=self.add_one(),col=0)
        w1.addWidget(self.analyseInternal, row=self.add_one(), col=0)
        w1.addWidget(self.amplitudeMapping, row=self.add_one(), col=0)
        w1.addWidget(self.btnViewLiveData, row=self.add_one(), col=0)


        w1.addWidget(self.save_trained_data, row=self.add_one(), col=0)
        w1.addWidget(self.load_trained_data, row=self.add_one(), col=0)
     

        w1.addWidget(dataTypeLabel, row=self.add_one(), col=0)
        w1.addWidget(self.btnIsNormal,row=self.add_one(),col=0)
        w1.addWidget(self.btnPacing,row=self.add_one(), col=0)

        # w1l.setAlignment(QtCore.Qt.AlignTop)

        self.d_control.addWidget(w1, row=1, colspan=1)



    def add_dock_widgets_plots(self):

        self.w1 = pg.PlotWidget(title="Plots of the slow-wave data")
        self.w2 = pg.PlotWidget(title="Plots of zoomed-in slow-wave data")
        self.w3 = pg.PlotWidget(title="Selected Data for Training")
        c = pg.PlotCurveItem(pen=pg.mkPen('r', width=2))
        c_event = pg.PlotCurveItem(pen=pg.mkPen('y', width=2))
        self.curve_bottom.append(c)
        self.curve_bottom.append(c_event)
        self.w3.addItem(c)
        self.w3.addItem(c_event)
        nPlots = 256

        self.w1.setYRange(0, 100)
        self.w1.setXRange(0, 3000)    


        for i in range(nPlots):
            c1 = pg.PlotCurveItem(pen=(i, nPlots))
            c1.setPos(0, i)
            self.curves_left.append(c1)
            self.w1.addItem(c1)

            c2 = pg.PlotCurveItem(pen=(i, nPlots))
            c2.setPos(0, i)
            self.curves_right.append(c2)
            self.w2.addItem(c2)


        self.s1 = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 120))
        self.s2 = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 120))
        self.w1.addItem(self.s1)
        self.w2.addItem(self.s2)
        self.d_plot.addWidget(self.w1, row=0, col=0)
        self.d_plot.addWidget(self.w2, row=0, col=1)
        self.d_train.addWidget(self.w3, row=0, col=0)
        self.proxy = pg.SignalProxy(self.w2.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.w2.scene().sigMouseClicked.connect(self.onClick)
        self.w2.sigXRangeChanged.connect(self.updateRegion)
        self.w2.sigYRangeChanged.connect(self.updateRegion)



    def set_crosshair(self):
        """
        Cross hair definition and initiation
        """
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.w2.addItem(self.vLine, ignoreBounds=True)
        self.w2.addItem(self.hLine, ignoreBounds=True)



    def set_rect_region_ROI(self):
        '''
        Rectangular selection region
        '''
        self.rect = pg.RectROI([300, 5], [1500, 10], pen=pg.mkPen(color='y', width=2))
        self.w1.addItem(self.rect)
        self.rect.sigRegionChanged.connect(self.updatePlot)



    def set_curve_item(self, nPlots, nSamples):
        self.w1.setYRange(0, 100)
        self.w1.setXRange(0, 3000)    
            
        for i in range(nPlots):
            c1 = pg.PlotCurveItem(pen=(i, nPlots))
            self.w1.addItem(c1)
            c1.setPos(0, i)
            self.curves_left.append(c1)

            self.w1.resize(600, 10)

            c2 = pg.PlotCurveItem(pen=(i, nPlots))
            self.w2.addItem(c2)
            c2.setPos(0, i)
            self.curves_right.append(c2)
            self.w2.showGrid(x=True, y=True)
            self.w2.resize(600, 10)

        self.updatePlot()



    def set_plot_data(self, data, nPlots, nSize):
        
        self.data = data
        # self.trainingDataPlot.set_plot_data(data)
        self.set_curve_item(nPlots, nSize)

        for i in range(nPlots):
            self.curves_left[i].setData(data[i])
            self.curves_right[i].setData(data[i])

        self.w1.setYRange(0, 100)

        xAxisMax = np.min([data.shape[1], 5000])
        self.w1.setXRange(0, xAxisMax)   

        ax = self.w1.getAxis('bottom')    #This is the trick  

        tickInterval = int(xAxisMax / 6) # Produce 6 tick labels per scroll window

        tickRange = range(0, data.shape[1], tickInterval)

        # Convert indices to time for ticks -- multiply indices by time between samples and add original starting time.
        tickLabels = [str(round(i*cg.dat['SigPy']['timeBetweenSamples']+cg.dat['SigPy']['timeStart'],2)) for i in tickRange]

        print(tickLabels)

        ticks = [list(zip(tickRange, tickLabels))]
        print(ticks)


        ax.setTicks(ticks)
             # self.xLabels = "print xLabels."
        # ax.setTicks([self.xLabels])


    def updatePlot(self):

        xpos = self.rect.pos()[0]
        ypos = self.rect.pos()[1]
        width = self.rect.size()[0]
        height = self.rect.size()[1]
        self.w2.setXRange(xpos, xpos+width, padding=0)
        self.w2.setYRange(ypos, ypos+height, padding=0)



    def updateRegion(self):

        xpos = self.w2.getViewBox().viewRange()[0][0]
        ypos = self.w2.getViewBox().viewRange()[1][0]
        self.rect.setPos([xpos, ypos], update=False)



    def repaint_plots(self):

        self.curves_left = []
        self.curves_right = []
        self.curve_bottom = []
        self.add_dock_widgets_plots()
        self.set_crosshair()
        self.set_rect_region_ROI()
        self.elec = []
        self.data = []
        
        self.trainingDataPlot = TrainingDataPlot()
        self.saveBtn_events.clicked.connect(lambda: self.add_as_events())
        self.saveBtn_nonEvents.clicked.connect(lambda: self.add_non_events())
        self.undoBtn.clicked.connect(lambda: self.undo())
        self.writeWEKABtn.clicked.connect(lambda: self.writeWEKA_data())
        self.readPredictedVal.clicked.connect(lambda: self.read_predicted())
        self.amplitudeMapping.clicked.connect(lambda: self.plot_amplitude_map())
        self.btnViewLiveData.clicked.connect(lambda: self.view_live_data())

        self.analyseInternal.clicked.connect(lambda: self.analyse_internal())

        self.save_trained_data.clicked.connect(lambda: self.save_trained())
        self.load_trained_data.clicked.connect(lambda: self.load_trained())


    def mouseMoved(self, evt):
        pos = evt[0]
        vb = self.w2.plotItem.vb
        if self.w2.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())


    def onClick(self, evt):

        pos = evt.scenePos()
        vb = self.w2.plotItem.vb
        if self.w2.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            self.elec.append([int(round(mousePoint.y()/1.2)), int(round(mousePoint.x()))])
            self.trainingDataPlot.add_region([int(round(mousePoint.y()/1.2)), int(round(mousePoint.x()))])

    """
    The binding functions for different gui command buttons.
    """
    def add_as_events(self):

        self.trainingDataPlot.add_events()
        self.curve_bottom[0].set_plot_data(self.trainingDataPlot.plotDat.flatten()[0:self.trainingDataPlot.plotLength * 36])
        self.curve_bottom[1].set_plot_data(np.repeat(self.trainingDataPlot.plotEvent.flatten()[0:self.trainingDataPlot.plotLength], 36))
        self.w3.setXRange(0, self.trainingDataPlot.plotLength * 36, padding=0)
        self.w3.setYRange(0, 1, padding=0)


    def add_non_events(self):

        self.trainingDataPlot.add_non_events()
        self.curve_bottom[0].set_plot_data(self.trainingDataPlot.plotDat.flatten()[0:self.trainingDataPlot.plotLength * 36])
        self.curve_bottom[1].set_plot_data(np.repeat(self.trainingDataPlot.plotEvent.flatten()[0:self.trainingDataPlot.plotLength], 36))
        self.w3.setXRange(0, self.trainingDataPlot.plotLength * 36, padding=0)
        self.w3.setYRange(0, 1, padding=0)


    def undo(self):

        self.trainingDataPlot.undo()
        self.curve_bottom[0].set_plot_data(self.trainingDataPlot.plotDat.flatten()[0:self.trainingDataPlot.plotLength])
        self.curve_bottom[1].set_plot_data(self.trainingDataPlot.plotEvent.flatten()[0:self.trainingDataPlot.plotLength])
        self.w3.setXRange(0, self.trainingDataPlot.plotLength * 36, padding=0)
        self.w3.setYRange(0, 1, padding=0)


    def read_predicted(self):

        filename = QtGui.QFileDialog.getOpenFileName(None, 'Open ARFF WEKA generated output file')
        if filename == u'':
            return
        test = ARFFcsvReader(filename)
        prediction = np.asarray(test.get_prediction())
        diff = np.diff(prediction)
        linear_at = np.array(np.where(diff == 1))
        pos = []
        length = len(self.data[1])
        for val in linear_at.transpose():
            pos.append([int(val/length), int(val % length)])
        pos_np = np.asarray(pos).transpose()

        self.s1.addPoints(x=pos_np[1], y=(pos_np[0]))
        self.s2.addPoints(x=pos_np[1], y=(pos_np[0]))


    def writeWEKA_data(self):

        test_data = np.reshape(self.data, -1)
        data = self.trainingDataPlot.plotDat[0][0:self.trainingDataPlot.plotLength]
        events = self.trainingDataPlot.plotEvent[0][0:self.trainingDataPlot.plotLength]/5
        Process(target=self.process_thread, args=(data, events)).start()
        Process(target=self.process_thread, args=[test_data]).start()


    def process_thread(self, data, event=None):

        training_analyser = FeatureAnalyser()
        # FeatureAnalyser requires the 1d data to be passed as array of an array
        training_features = training_analyser.writeWEKA_data([data],(1, self.trainingDataPlot.plotLength))
        if event is None:
            output_name = cg.test_file_name
        else:
            output_name = cg.training_file_name
        weka_write = WekaInterface(training_features, output_name)
        weka_write.arff_write(event)




    def analyse_internal(self):

        self.s1.clear()
        self.s2.clear()

        self.statBar.showMessage("Training and classifying. . .")

        testData = np.reshape(self.data, -1)

        windowSize = 36
        overlap = 0.2
        samples = []
        for j in range(1,len(testData)-1, int(overlap * windowSize)):
            if (len(testData[j:j+windowSize]) == windowSize):
                samples.append(testData[j:j+windowSize])
        
        sample_np = np.empty((len(samples), windowSize))

        for i, x in enumerate(samples):
            sample_np[i] = np.array(x)

        cnnType = self.btnIsNormal.isChecked()
            
        # Call classification function on test data and return the predictions

        swCNN = SlowWaveCNN(self.trainingDataPlot.plotDat[0:self.trainingDataPlot.plotLength, :], self.trainingDataPlot.plotEvent[0:self.trainingDataPlot.plotLength, :])
        preds = swCNN.classify_data(sample_np, cnnType)

        
        # Plot the prediction outputs 
        prediction = np.zeros((len(testData)), dtype=int);

        count = 0
        swLocs = np.where(preds==1)[0]

        print("Number sw raw predictions: ", len(swLocs))
        print("Number of preds: ", len(preds))
        print("Testdata.shape ", testData.shape)


        winRange = 0
        winRangeMultiplier = 2 * windowSize

        # for every x segment of data. if there are SW predictions within this segment, mark as sw.
        for j in range(0, len(testData), int(overlap * windowSize)):

            count += 1

            if (len(np.where(swLocs == count)[0]) > 0 and (j > winRange)) :
                baselinedDat = testData[j : j+(winRangeMultiplier)]
                maxIndex = np.argmax(np.absolute(baselinedDat - baselinedDat.mean(axis=0)))
                prediction[j+maxIndex] = 1
                winRange = j + winRangeMultiplier #skip next 2 windows


        print("prediction.shape: ", prediction.shape)

        print("nSW Predictions to X locations: ", len(np.where(prediction == 1)[0]))

        linear_at_uncorrected = np.array(np.where(prediction == 1))
        # linear_at_uncorrected = np.array(np.where(preds == 1))

        rows, cols = linear_at_uncorrected.shape
        to_remove_index = []

        # Remove duplicated values ?
        # for i in range(cols - 1):
        #     if (linear_at_uncorrected[0][i + 1] - linear_at_uncorrected[0][i] < 60) :
        #         to_remove_index.append(i + 1)

        # # Clear duplicated values to stop their removal
        # to_remove_index = []

        # linear_at = np.delete(linear_at_uncorrected, to_remove_index)
        linear_at = linear_at_uncorrected

        pos = []
        lengthData = len(self.data[0])
        nChans = self.data.shape[0]
        sync_events = []

        # Check for sync events
        for val in linear_at.transpose():
            sync_events.append(int(val % lengthData))

        # remove_sync_point = set([x for x in sync_events if sync_events.count(x) > 600])

        # # Clear sync points that are marked for removal:
        # remove_sync_point.clear()

        # Remove the sync events from the actual array

        # for val in linear_at.transpose():
        for swPred in linear_at.transpose():
            # if int(swPred % lengthData) not in remove_sync_point:
            xIndex = int(swPred / lengthData)
            yChannel = int((swPred % lengthData))
            pos.append([xIndex, yChannel])

        pos_np = np.asarray(pos).transpose()

        print("self.data.shape: ", self.data.shape)
        print("pos_np[1].size: ", pos_np[1].size)


        if pos_np.size is 0:
            print("No events detected")
            return

        self.s1.addPoints(x=pos_np[1], y=(pos_np[0]+0.75))
        self.s2.addPoints(x=pos_np[1], y=(pos_np[0]+0.75))

        # Convert event co-ordinates to indices for  2d TOA to output to GEMS
        self.statBar.showMessage("Finished classifying slow wave events.", 1000)

        update_GEMS_data_with_TOAs(pos_np, nChans)        



    def btn_animation_set_play(self):

        print("Setting play button")

        btnPlayIconPath = cg.graphicsPath + "btnPlayTiny.png"

        self.btnPlayPause.setIcon(QtGui.QIcon(btnPlayIconPath))
        try:
            self.btnPlayPause.clicked.disconnect()
        except Exception, e:
            print(e)

        self.btnPlayPause.clicked.connect(self.play_animation)            



    def btn_animation_set_pause(self):

        print("Setting pause button")

        self.btnPlayPause.setFixedHeight(20)
        self.btnPlayPause.setFixedWidth(20)

        btnPauseIconPath = cg.graphicsPath + "btnPauseTiny.png"

        self.btnPlayPause.setIcon(QtGui.QIcon(btnPauseIconPath))
        self.btnPlayPause.setIconSize(QtCore.QSize(20,20))

        try:
            self.btnPlayPause.clicked.disconnect()
        except Exception, e:
            print(e)

        self.btnPlayPause.clicked.connect(self.pause_animation)



    def play_animation(self):
        self.ampMap.Playing = True

        self.ampMap.play(self.ampMap.currentFrameRate)
        self.btn_animation_set_pause()



    def pause_animation(self):
        self.ampMap.Playing = False

        self.ampMap.play(0)
        self.btn_animation_set_play()



    def change_animation_data_to_chans(self) :

        self.ampMap.gridDataToAnimate = cg.dat['SigPy']['gridChannelData']
        self.change_animation_data()



    def change_animation_data_to_events(self) :

        self.ampMap.gridDataToAnimate = cg.dat['SigPy']['gridEventData']
        self.change_animation_data()



    def change_animation_data(self) :

        self.ampMap.priorIndex = self.ampMap.currentIndex        
        self.ampMap.currentIndex = self.ampMap.priorIndex
        self.ampMap.setLevels(0.5, 1.0)


        self.ampMap.setImage(self.ampMap.gridDataToAnimate)

        self.play_animation()        



    def change_frameRate(self, intVal):

        self.ampMap.currentFrameRate = intVal
        fpsLabelStr = str(round((self.ampMap.currentFrameRate / self.ampMap.realFrameRate),1)) + " x"
        self.fpsLabel.setText(fpsLabelStr)

        if self.ampMap.Playing == True :
            self.ampMap.play(self.ampMap.currentFrameRate)



    def plot_amplitude_map(self):

        # Create animation window
        self.ampMap = pg.ImageView()
        self.ampMap.setWindowTitle("Mapped Animating")

        # Preload data

        cg.dat['SigPy']['gridChannelData'] = map_channel_data_to_grid()



        if 'toaIndx' not in cg.dat['SigPy'] :
            self.statBar.showMessage("Note! To plot CNN SW event data, please first run analyse events.")
        else:
            cg.dat['SigPy']['gridEventData'] = map_event_data_to_grid_with_trailing_edge()

        gridDataToAnimate = cg.dat['SigPy']['gridChannelData']


        self.ampMap.setImage(gridDataToAnimate)
        self.ampMap.show()        

        ## ======= TOP NAV ===========
        ## -- Play pause speed controls
        # Set default animation speed to sampling frequency fps
        self.ampMap.singleStepVal = round((cg.dat['SigPy']['sampleRate'] / 2), 1)

        self.ampMap.currentFrameRate = cg.dat['SigPy']['sampleRate']
        self.ampMap.realFrameRate = cg.dat['SigPy']['sampleRate']
        self.ampMap.currentFrameRate = self.ampMap.realFrameRate * 2 # Start at double speed

        # Create play pause speed controls
        self.btnPlayPause = QtGui.QPushButton('')
        self.btn_animation_set_pause()

        self.speedSlider = QtGui.QSlider()
        self.speedSlider.setOrientation(QtCore.Qt.Horizontal)
        self.speedSlider.setMinimum(0)        
        self.speedSlider.setMaximum(self.ampMap.singleStepVal * 16)
        self.speedSlider.setValue(self.ampMap.currentFrameRate)


        self.speedSlider.setSingleStep(self.ampMap.singleStepVal)
        
        self.speedSlider.valueChanged.connect(self.change_frameRate)

        fpsLabelStr = str(round((self.ampMap.currentFrameRate / self.ampMap.realFrameRate),1)) + " x"
        self.fpsLabel = QtGui.QLabel(fpsLabelStr)


        ## -- Data select -- live / events / amplitude
        self.radioGrpAnimationData = QtGui.QButtonGroup() 

        self.btnAmplitude = QtGui.QRadioButton('Amplitude')
        self.btnCNNEvents = QtGui.QRadioButton('CNN Events')
        self.btnLive = QtGui.QRadioButton('Live')


        self.btnAmplitude.clicked.connect(self.change_animation_data_to_chans)
        self.btnCNNEvents.clicked.connect(self.change_animation_data_to_events)        

        self.btnAmplitude.setChecked(1);

        self.radioGrpAnimationData.addButton(self.btnAmplitude, 0)
        self.radioGrpAnimationData.addButton(self.btnCNNEvents, 1)


        self.radioGrpAnimationData.setExclusive(True)        


        ## -- Add toolbar widgets to a proxy container widget 
        self.LayoutWidgetPlayPauseSpeed = QtGui.QWidget()
        self.qGridLayout = QtGui.QGridLayout()

        self.qGridLayout.setHorizontalSpacing(14)

        self.qGridLayout.setContentsMargins(8,0,8,0)

        self.qGridLayout.addWidget(self.btnPlayPause, 0,0, alignment=1)
        self.qGridLayout.addWidget(self.speedSlider, 0,1, alignment=1)
        self.qGridLayout.addWidget(self.fpsLabel, 0,2, alignment=1)

        self.qGridLayout.addWidget(self.btnAmplitude, 0,3, alignment=1)
        self.qGridLayout.addWidget(self.btnCNNEvents, 0,4, alignment=1)

        self.LayoutWidgetPlayPauseSpeed.setLayout(self.qGridLayout)

        self.proxyWidget = QtGui.QGraphicsProxyWidget()
        self.proxyWidget.setWidget(self.LayoutWidgetPlayPauseSpeed)
        self.proxyWidget.setPos(0, 0)    

        print("self.ampMap.ui: ", self.ampMap.ui)

        self.ampMap.scene.addItem(self.proxyWidget)

        # Automatically start animation
        self.play_animation()


    def preprocess_buffer_and_housekeeping(self):

        winStartIndex = self.LiveData.priorBufferedChunk.shape[1]
        preprocessWindowChunks = np.hstack((self.LiveData.priorBufferedChunk, self.LiveData.bufferedChunk))
    

        # Reset buffer keeping only the last frame in memory

        self.lastFrame = self.LiveData.bufferedChunk[:,(self.nSamplesCaptured-1)].reshape(-1,1)                
        self.LiveData.bufferedChunk = self.lastFrame
        print("Buffer Reset!")

        # Increase buffer size until it reaches self.desiredPriorChunkSize
        priorBufferChunkStartIndex = preprocessWindowChunks.shape[1] - self.desiredPriorChunkSize

        if priorBufferChunkStartIndex > 0 :
            self.LiveData.priorBufferedChunk = preprocessWindowChunks[:,winStartIndex:]

        else :            
             self.LiveData.priorBufferedChunk = preprocessWindowChunks
        

        preprocessedData = preprocess(preprocessWindowChunks)
        # preprocessedData = preprocessWindowChunks

        self.mappedPreprocessedData = map_channel_data_to_grid(preprocessedData[:, winStartIndex:])       
        print("self.mappedPreprocessedData.shape: ", self.mappedPreprocessedData.shape)



    # Display chunk at a rate matching the capture rate
    def live_animate(self) :

        timeBetweenSamplesAdjust = (self.nSamplesPerChunkIdealised * self.LiveData.timeBetweenSamples / self.nSamplesCaptured)
        timeStartDisplayingFrames = time.time()

        # self.liveMapViewBox.removeItem(self.liveMapImageItem)
        # self.liveMapViewBox.addItem(self.liveMapImageItem)

        for frame in range(0, self.mappedPreprocessedData.shape[0] ) :

            try:
                self.lockDisplayThread.acquire() 
                self.liveMapImageItem.setImage(self.mappedPreprocessedData[frame,:,:])
                self.lockDisplayThread.release() 

            except Exception, e:
                print(e)

            nextFrameTime = timeStartDisplayingFrames + frame * timeBetweenSamplesAdjust
            # print("nextFrameTime: ",nextFrameTime)
            # print("currentFrameTime: ",time.time())
            sleepTime = nextFrameTime - time.time()
            # print("sleepTime: ", sleepTime)

            if sleepTime > 0 :
                time.sleep(sleepTime)

        print(frame," frames displayed.")





    # Thread to keep pulling in live data 
    def read_liveData_buffer_Thread(self):

        print("In data pulling thread")
        print("self.LiveData.timeBetweenSamples: ", self.LiveData.timeBetweenSamples)
        self.nSamplesPerChunkIdealised = 30
        self.desiredPriorChunkSize =  self.nSamplesPerChunkIdealised * 4


        self.priorBufferedChunk = self.LiveData.bufferedChunk

        while True:

            # Get number of samples captured
            self.nSamplesCaptured = self.LiveData.bufferedChunk.shape[1]
            print("Frames captured: ", self.nSamplesCaptured)
            # print("nSamplesCaptured: ",self.nSamplesCaptured)

            # If number of samples captured exceeds the idealised buffer size
            # then preprocess, reset buffer and animate

            if self.nSamplesCaptured >= self.nSamplesPerChunkIdealised :

                # print("nSamplesCaptured ",self.nSamplesCaptured," meets criteria.")

                self.preprocess_buffer_and_housekeeping()

                # Live animation
                self.live_animate()

            else:

                # Buffer isn't big enough, give it some more time to produce frames
                time.sleep(0.01)
            
            if not self.liveMapWin.isVisible():

                print("Display thread stopping.")
                self.LiveData.shouldStop = True
                break



    def view_live_data(self) :

        print("Starting live view data")

        # Create thread to capture (or simulate) live data
        self.LiveData = LiveData()

        # Check if live data capture thread has been started -- if not, start
        if not self.LiveData.isAlive():
            try:
                self.LiveData.start()
            except (KeyboardInterrupt, SystemExit):
                sys.exit()   


        # Create image item
        self.liveMapWin = pg.GraphicsWindow() 
        self.liveMapWin.setWindowTitle('Live Mapping')


        self.liveMapViewBox = self.liveMapWin.addViewBox()

        self.liveMapWin.setCentralItem(self.liveMapViewBox)
        self.liveMapViewBox.setAspectLocked()

        # ui.graphicsView.setCentralItem(vb)

        self.liveMapImageItem = pg.ImageItem()
        self.liveMapViewBox.addItem(self.liveMapImageItem)

        # self.liveMapWidgetLayout = pg.LayoutWidget()

        # self.liveMapWin.setLayout(self.liveMapGraphicsLayout)

        # self.liveMapViewBox.addItem(self.liveMapRawImageWidget)

        self.lockDisplayThread = threading.Lock()


        print("Attemping to start data viewing thread")
        self.displayLiveDataThread = Thread(name='read_liveData_buffer_Thread', target=self.read_liveData_buffer_Thread)
        
        if not self.displayLiveDataThread.isAlive():
            try:
                self.displayLiveDataThread.start()
            except (KeyboardInterrupt, SystemExit):
                sys.exit()         



    def save_trained(self):
        with open(cg.trained_file, 'wb') as output:
            pickle.dump(self.trainingDataPlot, output, pickle.HIGHEST_PROTOCOL)


    def load_trained(self):
        self.trainingDataPlot = np.load(cg.get_trained_file())
        self.curve_bottom[0].set_plot_data(self.trainingDataPlot.plotDat.flatten()[0:self.trainingDataPlot.plotLength])
        self.curve_bottom[1].set_plot_data(self.trainingDataPlot.plotEvent.flatten()[0:self.trainingDataPlot.plotLength])
        self.w3.setXRange(0, self.trainingDataPlot.plotLength, padding=0)
        self.w3.setYRange(-10, 10, padding=0)




    ## ==== MENU BAR ACTIONS ====

    def load_file_selector__gui_set_data(self):
        # filenames = QtGui.QFileDialog.getOpenFileNames(self.loadAction, "Select File", "", "*.txt")
        cg.datFileName = QtGui.QFileDialog.getOpenFileName(None, "Select File", "", "*.mat")

        if not (sys.platform == "linux2") :
            cg.datFileName = cg.datFileName[0]

        self.statBar.showMessage("Loading . . . ", 1000)
        print("cg.datFileName: ", cg.datFileName)        
        load_GEMS_mat_into_SigPy(cg.datFileName)

        self.statBar.showMessage("Finished loading! Now preprocessing . . .")

        cg.dat['SigPy']['normData'] = preprocess(cg.dat['SigPy']['filtData'])
        self.statBar.showMessage("Finished pre-processing! Now repainting plots . . . ")

        # print("cg.dat['SigPy']['normData']: ", cg.dat['SigPy']['normData'])
        # self.trainingDataPlot = TrainingDataPlot()


        self.repaint_plots()
        # Set plot data
        self.set_plot_data(cg.dat['SigPy']['normData'], cg.dat['SigPy']['normData'].shape[0], cg.dat['SigPy']['normData'].shape[1])
        self.btnIsNormal.setChecked(1)

        self.statBar.showMessage("Finished repainting plots!", 2000)



    def save_as_file_selector(self):

        cg.datFileName = QtGui.QFileDialog.getSaveFileName(None, "Save As File", cg.datFileName, "*.mat")

        if not (sys.platform == "linux2") :
            cg.datFileName = cg.datFileName[0]        
        self.statBar.showMessage("Saving . . . ")
        print("cg.datFileName: ", cg.datFileName) 

        save_GEMS_SigPy_file(cg.datFileName)

        self.statBar.showMessage("Saved file!")
      


    def save_file_selector(self):
        self.statBar.showMessage("Saving . . . ")
        save_GEMS_SigPy_file(cg.datFileName)

        self.statBar.showMessage("Saved file!")


    def exit_app(self) :
        self.win.close()
        sys.exit()