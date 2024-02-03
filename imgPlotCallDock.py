'''
画像の分析を行うためのプロトタイピング用のコード
2021/10/02

'''
import sys
import numpy as np
# from PyQt5 import QtWidgets, QtGui, QtCore
# from PyQt5.QtWidgets import QTreeView, QTreeWidgetItem, QMessageBox, QApplication,QFileSystemModel, QVBoxLayout
# from PyQt5.QtGui import QIcon, QImage, QPalette, QPixmap
# from PyQt5.QtWebEngineWidgets import QWebEngineView  # pip install PyQtWebEngine

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtWidgets import QTreeView, QTreeWidgetItem, QMessageBox, QFileSystemModel,QApplication, QVBoxLayout
from PySide6.QtGui import QIcon, QImage, QPalette, QPixmap
from PySide6.QtWebEngineWidgets import QWebEngineView  # pip install PyQtWebEngine


import io
import pyqtgraph as pg
from pyqtgraph.dockarea import *
#from numba import jit

import cv2

# uiファイル読み込み用
#from PyQt5 import uic

from datetime import datetime, timedelta
import os
import glob
import pandas as pd

# OS固有の設定
# どのPCでも、コードが書けるように。
# 
import platform
import folium

from numba import jit


from imgPlotDockUi import Ui_MainWindow 

# ライブラリ読み込み
from PIL import Image
import PIL.ExifTags as ExifTags


def get_gpspos_of_image(file):
    im = Image.open(file)
    exif = {
        ExifTags.TAGS[k]: v
        for k, v in im._getexif().items()
        if k in ExifTags.TAGS
    }
    # GPS情報を得る --- (*2)
    gps_tags = exif["GPSInfo"]
    gps = {
        ExifTags.GPSTAGS.get(t, t): gps_tags[t]
        for t in gps_tags
    }
    # 緯度経度情報を得る --- (*3)
    def conv_deg(v):
        # 分数を度に変換
        deg = float(v[0])
        min = float(v[1])
        sec = float(v[2])
        return deg + (min / 60.0) + (sec / 3600.0)
    lat = conv_deg(gps["GPSLatitude"])
    lon = conv_deg(gps["GPSLongitude"])
    return lat, lon

#class mainWindow(QtWidgets.QMainWindow):
#    def __init__(self, parent=None):
#        super().__init__(parent)

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.show()
        # uiファイル用
        #uic.loadUi('imgPlotDockUi.ui',self)
        # for pyfile
        #self.ui = Ui_MainWindow()
        #self.ui.setupUi(self)
        # pathを引数にて指定
        try:
            path = sys.argv[1]
        except IndexError:
            path = '.'
        self.filepath = []
        self.second_y = []
        
        self.model = QFileSystemModel()
        self.model.setRootPath(path)
        self.model.setNameFilters(['*.jpg','*.jpeg']) # この設定だけだと、非該当の拡張子はグレー表示
        self.model.setNameFilterDisables(False) # 上記フィルターに該当しないファイルは非表示


        # 呼び出しは、self.ui.treeView
        # TreeViewでないとあきまへん（treeWidgetはNG）
        view = self.treeView
        view.setModel(self.model)
        font = QtGui.QFont()
        # OSによってフォントサイズを変更
        osname = platform.system()
        if osname == 'Darwin':
            font.setPointSize(14)
            view.setFont(font)
            #self.listWData.setFont(font)
        elif osname == 'Windows':
            font.setPointSize(8)
            view.setFont(font)
            font.setPointSize(8)
            #self.listWData.setFont(font)            
        else:
            FontFamily = 'FreeSerif'
            
        # ラジオボタンの設定
        #self.upButton = self.sender()
        #self.upButton.setChecked(True)
        #view.setColumnWidth(0,260)
        #view.setColumnWidth(2,48)
        view.hideColumn(1)# for removing Size Column
        view.hideColumn(2)# for removing Type Column
        view.hideColumn(3)# for removing Date Modified Column
        view.setRootIndex(self.model.index(path))
        view.setItemsExpandable(True)        
        view.expandAll()
        view.selectionModel().currentChanged.connect(self.getFileName)
        #self.listWData.currentTextChanged.connect(self.secondY)

    def graphPlot(self, imgBGR, plotArea):
        #self.graphicsView.clear() # 画面を消す！
        self.dockWidget.clear()

        d1 = Dock('upper', size=(1, 1))
        #d2 = Dock('lower', size=(1, 1))
        self.dockWidget.addDock(d1, 'left')
        #self.dockWidget.addDock(d2, 'right')
        # <widget class="DockArea" name="dockWidget" native="true"/>
        # uiファイルの上記定義から、nameにDockを追加
        setprop = lambda x: (x.showGrid(x=True, y=True, alpha=0.75), x.showAxis('left'),x.setAutoVisible(y=True))

        ##
        ## 元画像（orgRGB）の表示用
        ##
        orgRGB = pg.PlotWidget() #ここでXの範囲を更新
        setprop(orgRGB)
        
        
        imgRGB = cv2.cvtColor(imgBGR, cv2.COLOR_BGR2RGB) #RGB
        im_list = np.array(imgRGB)
        img = pg.ImageItem(im_list)
        orgRGB.addItem(img, lockAspect=False)
        self.orgRGB = orgRGB
        # ROIの設定
        #print('imgBGR.shape[0]:',imgBGR.shape[0])
        #print('imgBGR.shape[1]:',imgBGR.shape[1])
        roi = pg.RectROI([0, 0],[imgBGR.shape[0]/2, imgBGR.shape[1]/2],pen=pg.mkPen('r',width=3),hoverPen=pg.mkPen('r',width=3),scaleSnap=True,translateSnap=True)        
        #roi = pg.RectROI([0, 0], [50, 50], pen=(0,9))
        roi.addScaleHandle([0, 0], [1, 1])  # bottom,left handles scaling both vertically and horizontally
        #roi.addScaleHandle([1, 1], [0, 0])  # top,right handles scaling both vertically and horizontally
        #roi.addScaleHandle([1, 0], [0, 1])  # bottom,right handles scaling both vertically and horizontally
        #roi.addScaleHandle([0, 1], [1, 0])
        '''
        addScaleHandle(pos, center, axes=None, item=None, name=None, lockAspect=False, index=None)
        Arguments
        
        pos
        (length-2 sequence) The position of the handle relative to the shape of the ROI. 
        A value of (0,0) indicates the origin, whereas (1, 1) indicates the upper-right corner, 
        regardless of the ROI's size.
        
        center
        (length-2 sequence) The center point around which scaling takes place. 
        If the center point has the same x or y value as the handle position, 
        then scaling will be disabled for that axis.
        
        item
        The Handle instance to add. If None, a new handle will be created.
        
        name
        The name of this handle (optional). Handles are identified by name 
        when calling getLocalHandlePositions and getSceneHandlePositions.
        
        roi.addScaleHandle([0, 0], [0, 0]) # 右上（動く）,左下（動かない）
        roi.addScaleHandle([0, 0], [1, 0]) # 右上（動く）,左下（右のみ）
        roi.addScaleHandle([0, 0], [1, 1]) # 右上（動く）,左下（動く）
        roi.addScaleHandle([0, 0], [0, 1]) # 右上（動く）,左下（上のみ）
        roi.addScaleHandle([0, 1], [0, 0]) # 左上（下のみ）,右上（動く）
        roi.addScaleHandle([0, 1], [1, 0]) # 左上（動く）,右上（動く）
        roi.addScaleHandle([0, 1], [1, 1]) # 左上（右のみ）,右上（動く）
        roi.addScaleHandle([0, 1], [0, 1]) # 左上（動かない）,右上（動く）
        roi.addScaleHandle([1, 0], [0, 0]) # 右上（動く）,右下（左のみ）
        roi.addScaleHandle([1, 0], [1, 0]) # 右上（動く）,右下（動かない）
        roi.addScaleHandle([1, 0], [1, 1]) # 右上（動く）,右下（上のみ）
        roi.addScaleHandle([1, 0], [0, 1]) # 右上（動く）,右下（動く）
        roi.addScaleHandle([1, 1], [0, 0]) # 右上（動く）
        roi.addScaleHandle([1, 1], [1, 0]) # 右上（下のみ）
        roi.addScaleHandle([1, 1], [1, 1]) # 右上（動かない）
        roi.addScaleHandle([1, 1], [0, 1]) # 右上（左のみ）
        '''
        roi.addScaleHandle([1, 0], [0, 1]) # 右上（動く）,右下（動く）
        
        #roi.addScaleHandle([0, 0], [0, 0])
        orgRGB.addItem(roi)
        roi.setZValue(10)  # make sure ROI is drawn above image
        # ROIで切り出した画像
        img_selected = pg.ImageItem() 

        ##
        ## 切り出した画像の表示用
        ##
        roiRGB = pg.PlotWidget()
        setprop(roiRGB)
        
        roiRGB.addItem(img_selected, lockAspect=True)
        
        #@jit
        def updateROI(roi):
            img_selected.setImage(roi.getArrayRegion(im_list, img))
            roiRGB.autoRange()

        roi.sigRegionChanged.connect(updateROI)
        updateROI(roi)

        #@jit
        def updateROI(roi):
            img_selected.setImage(roi.getArrayRegion(im_list, img))
            roiRGB.autoRange()

        roi.sigRegionChanged.connect(updateROI)
        updateROI(roi)

        #@jit
        def updatePlot():
            # Create the scatter plot and add it to the view
            selected = roi.getArrayRegion(im_list, img)
            ##
            ## 切り出した画像をHSV変換するよ
            ##
            #print('selected\n',selected.astype(np.float32))
            #print(len(selected.flatten())//3)
            #print('selected\n',selected.flatten().reshape(len(selected.flatten())//3, 3))
            pixel_colors = selected.astype(np.float32).flatten().reshape(len(selected.flatten())//3, 3)
            #pixel_colors = selected.astype(np.float32).reshape((np.shape(selected.astype(np.float32))[0]*np.shape(selected.astype(np.float32))[1], 3))
            #print('pixel_colors\n',pixel_colors)
            #selectedBGR = cv2.cvtColor(int(selected), cv2.COLOR_RGB2BGR) #RGB
            HSV_img = cv2.cvtColor(selected.astype(np.float32),cv2.COLOR_RGB2HSV_FULL)
            hue, saturation, value = cv2.split(HSV_img)
            roiHSV = pg.PlotWidget()
            setprop(roiHSV)
            test = pg.PlotDataItem(hue.flatten(), saturation.flatten(), clear=True, pen=None ,alpha=1, symbolBrush=pixel_colors, symbolPen=None ,symbolSize=7)
            roiHSV.setRange(xRange = (0, 360), padding = 0)
            #test = pg.PlotDataItem(hue.flatten(), saturation.flatten(), clear=True, pen=None ,alpha=1, symbolPen=None ,symbolSize=7)
            roiHSV.addItem(test)
            d1.addWidget(roiHSV,row=1, col=0)
            ##
            ## Lab表示用
            ## 


            Lab_img = cv2.cvtColor(selected.astype(np.float32), cv2.COLOR_RGB2LAB)
            print(Lab_img)
            L_value, a_value, b_value= cv2.split(Lab_img)
            roiLab = pg.PlotWidget()
            setprop(roiLab)
            test2 = pg.PlotDataItem(a_value.flatten(), L_value.flatten(), clear=True, pen=None ,alpha=1, symbolPen=None ,symbolSize=7)
            roiLab.addItem(test2)
            d1.addWidget(roiLab,row=1, col=1)
            
            '''
            ##
            ## RGB表示用
            ## 
            plotRGB = pg.PlotWidget()
            setprop(plotRGB)
            b, g, r = selected.astype(np.float32)[:,:,0], selected.astype(np.float32)[:,:,1], selected.astype(np.float32)[:,:,2]
            hist_r = cv2.calcHist([r],[0],None,[256],[0,256])
            hist_g = cv2.calcHist([g],[0],None,[256],[0,256])
            hist_b = cv2.calcHist([b],[0],None,[256],[0,256])
            num = np.arange(256)
            rhist = pg.PlotDataItem(num,hist_r.flatten(), pen=pg.mkPen('r',width=2), clear=True)
            ghist = pg.PlotDataItem(num,hist_g.flatten(), pen=pg.mkPen('g',width=2), clear=True)
            bhist = pg.PlotDataItem(num,hist_b.flatten(), pen=pg.mkPen('b',width=2), clear=True)
            plotRGB.addItem(rhist)
            plotRGB.addItem(ghist)
            plotRGB.addItem(bhist)
            d1.addWidget(plotRGB,row=0, col=3)
            '''


        roi.sigRegionChanged.connect(updatePlot)
        updatePlot()
        


        ##
        ## プロットエリアの切り替え用（未解決）
        ## 2021.10.5
        ##
        d1.addWidget(orgRGB,row=0, col=0)
        d1.addWidget(roiRGB,row=0, col=1)
        #elif plotArea == 'lower':
        #    d2.addWidget(orgRGB,row=0, col=0)
        #    d2.addWidget(roiRGB,row=0, col=1)
    

        # FilePathはここで指定
    def getFileName(self, index):
        plotArea = []
        try:
            indexItem = self.model.index(index.row(), 0, index.parent())# print(indexItem)
            if os.path.isfile(self.model.filePath(indexItem)):
                self.filepath.insert(0,self.model.filePath(indexItem))
                imgBGR = cv2.imread(self.filepath[0])
                #self.listWData.clear()
                self.graphPlot(imgBGR,plotArea)
                try:
                    lat, lon = get_gpspos_of_image(self.filepath[0])
                    posInfo = []
                    posInfo.append('Lat: '+str(lat))
                    posInfo.append('Lon: '+str(lon))
                    #imgInfo.append(('Width: '+ str(imgBGR.shape[1])))
                    #imgInfo.append(('Height: '+ str(imgBGR.shape[0])))
                    #imgInfo.append(('Ch: ' + str(imgBGR.shape[2])))
                    #self.listWData.addItems(posInfo)
                    #self.graphPlot(self.filepath[0],second_y='PID')        
                except AttributeError as e:
                    imgInfo = []
                    imgInfo.append(imgBGR.shape[0])
                    imgInfo.append(imgBGR.shape[1])
                    imgInfo.append(imgBGR.shape[2])
                    #self.listWData.addItems(imgInfo)                    
            else:
                pass
                #QMessageBox.warning(None, "Notice!", "Select File!", QMessageBox.Yes)
        except AttributeError as e:
            pass
        #print('File Path :', self.filepath[0],type(self.filepath[0]))   

if __name__ == '__main__':
    from pyqtgraph.dockarea.Dock import DockLabel
    def updateStyle(self):
        self.setStyleSheet("DockLabel { color: #FFF; background-color: #444; }")
    setattr(DockLabel, 'updateStyle', updateStyle)
    
    style = """
        QWidget { color: #AAA; background-color: #333; border: 0px; padding: 0px; }
        QWidget:item:selected { background-color: #666; }
        QMenuBar::item { background: transparent; }
        QMenuBar::item:selected { background: transparent; border: 1px solid #666; }
    """
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec())
