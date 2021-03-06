from signal_processing.preprocessing import *

from signal_processing.livedata import LiveData
from signal_processing.mapping import *

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

from threading import Thread
import threading
import time

class AnimateLive():

    def __init__(self):
        self.nSamplesPerChunkIdealised = 30
        self.desiredChunkSizeMultiplier = 4
        self.animate_live_data()


    def animate_live_data(self) :

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

        self.liveMapImageItem = pg.ImageItem()
        self.liveMapViewBox.addItem(self.liveMapImageItem)



        self.lockDisplayThread = threading.Lock()

        print("Attemping to start data viewing thread")
        self.displayLiveDataThread = Thread(name='read_liveData_buffer_Thread', target=self.read_liveData_buffer_Thread)
        
        if not self.displayLiveDataThread.isAlive():
            try:
                self.displayLiveDataThread.start()
            except (KeyboardInterrupt, SystemExit):
                sys.exit()  



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


        
    # Thread to keep pulling in live data 
    def read_liveData_buffer_Thread(self):

        print("In data pulling thread")
        print("self.LiveData.timeBetweenSamples: ", self.LiveData.timeBetweenSamples)
        self.desiredPriorChunkSize =  self.nSamplesPerChunkIdealised * self.desiredChunkSizeMultiplier

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

            except Exception as e:
                print(e)

            nextFrameTime = timeStartDisplayingFrames + frame * timeBetweenSamplesAdjust

            sleepTime = nextFrameTime - time.time()

            if sleepTime > 0 :
                time.sleep(sleepTime)

        print(frame," frames displayed.")                



        


