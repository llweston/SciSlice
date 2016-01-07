# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 16:45:00 2015

@author: lvanhulle
"""

import gcode as gc
import parameters as pr
import Point as p
import InFill as Inf
import LineGroup as lg
from parameters import constants as c
from Shape import Shape
from operator import itemgetter
import numpy as np
import time

class Figura:
    
    def __init__(self, inShapes):
        startTime = time.time()
        layer = self.organizedLayer(inShapes)
        print '\nLayer organized in: %.2f sec\n' %(time.time() - startTime)
        with open('I:\RedBench\static\data\LineList.txt', 'w') as f:
            f.write('test\n')
            f.write(layer.CSVstr())
        self.gcode = '' + gc.startGcode()
        self.partCount = 1
        for partParams in pr.everyPartsParameters:
            print 'Part Count: ' + str(self.partCount)            
            print 'Part Params: ' + str(partParams)
            part = self.part_Gen(layer, partParams)
            self.gcode += ';\n\nPart number: ' + str(self.partCount) + '\n'
            self.gcode += ';Parameters: ' + str(partParams) + '\n'
            self.setGcode(part, partParams[c.PRINT_SPEED], partParams[c.EXTRUSION_RATE])
            self.partCount += 1
        self.gcode += gc.endGcode()
    
    def part_Gen(self, baseLayer, partParams):
        for i in range(partParams[c.NUM_LAYERS]):
            yield baseLayer.translate(partParams[c.SHIFT_X], partParams[c.SHIFT_Y],
                                      partParams[c.LAYER_HEIGHT]*(i+1))
    
    def setGcode(self, part, printSpeed, extrusionRate):
        layerNumber = 1
        self.gcode += gc.newPart()
        totalExtrusion = 0
        
        for layer in part:
            self.gcode += ';Layer: ' + str(layerNumber) + '\n'
            self.gcode += ';T' + str(self.partCount) + str(layerNumber) + '\n'
            self.gcode += ';M6\n'
            self.gcode += gc.rapidMove(layer[0].start, pr.INCLUDE_Z)
            self.gcode += gc.firstApproach(layer[0].start)
            
            for line in layer:
                line.extrusionRate = extrusionRate
                totalExtrusion += line.length*line.extrusionRate
                self.gcode += gc.rapidMove(line.start, pr.OMIT_Z)
                self.gcode += gc.feedMove(line.end, pr.OMIT_Z, totalExtrusion, printSpeed)
            
            self.gcode += gc.retractLayer(totalExtrusion, layer[-1].end)
            self.gcode += '\n\n'
            layerNumber += 1        
                
    def organizedLayer(self, inShapes):
        layer = lg.LineGroup()
        
        lineCoros = {i : inShapes[i].nearestLine_Coro(i) for i in range(len(inShapes))}
        for key, coro in lineCoros.iteritems():
            next(coro)
        
        lastPoint = p.Point(0,0)
        index = -1        
        while True:
            results = []
            for key in lineCoros.keys():
                try:
                    results.append(lineCoros[key].send(
                        (True if key == index else False, lastPoint)))
                except StopIteration:
                    del lineCoros[key]
            if len(results) == 0: break
            line, index = min(results, key=itemgetter(2))[:2]
            lastPoint = line.end
            layer.append(line)
            if isinstance(inShapes[index], Shape):
                while True:
                    try:
                        line = lineCoros[index].send((True, lastPoint))[0]
                    except StopIteration:
                        del lineCoros[index]
                        break
                    else:
                        lastPoint = line.end
                        layer.append(line)
        return layer
    
    def __str__(self):
        tempString = ''
        layerNumber = 1
        for layer in self.layers:
            tempString += ';T' + str(layerNumber) + '\n'
            tempString += ';M6\n'
            tempString += str(layer)
            layerNumber += 1
        return tempString
    
