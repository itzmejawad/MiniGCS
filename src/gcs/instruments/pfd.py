# -*- coding: utf-8 -*-
'''
Port from qgroundcontrol PFD
'''
import math

from PyQt5.QtCore import (QPoint, QPointF, QRectF, Qt, QTimer,
                          pyqtSignal, qRound)
from PyQt5.QtGui import (QBrush, QColor, QFont, QFontMetrics, QLinearGradient,
                         QPainter, QPainterPath, QPen)
from PyQt5.QtWidgets import QSizePolicy, QWidget
from UserData import UserData
from utils import unused

UD_PFD_KEY = 'PFD'
UD_PFD_PRIMARY_SPEED_SOURCE_KEY = 'PRIMARY_SPEED_SOURCE'
UD_PFD_PRIMARY_ALTITUDE_SOURCE_KEY = 'PRIMARY_ALTITUDE_SOURCE'

class PrimaryFlightDisplay(QWidget):
    ROLL_SCALE_RANGE = 60
    ROLL_SCALE_TICKMARKLENGTH = 0.04
    ROLL_SCALE_RADIUS = 0.42
    ROLL_SCALE_MARKERWIDTH = 0.06
    ROLL_SCALE_MARKERHEIGHT = 0.04
    LINEWIDTH = 0.0036
    SMALL_TEXT_SIZE = 0.03
    MEDIUM_TEXT_SIZE = SMALL_TEXT_SIZE * 1.2
    LARGE_TEXT_SIZE = MEDIUM_TEXT_SIZE * 1.2
    PITCH_SCALE_RESOLUTION = 5
    PITCH_SCALE_HALFRANGE = 15
    PITCH_SCALE_MAJORWIDTH = 0.1
    PITCH_SCALE_MINORWIDTH = 0.066
    PITCH_SCALE_WIDTHREDUCTION_FROM = 30
    PITCH_SCALE_WIDTHREDUCTION = 0.3
    SHOW_ZERO_ON_SCALES = True
    CROSSTRACK_MAX = 1000
    CROSSTRACK_RADIUS = 0.6
    COMPASS_DISK_MAJORTICK = 10
    COMPASS_DISK_ARROWTICK = 45
    COMPASS_DISK_MAJORLINEWIDTH = 0.006
    COMPASS_DISK_MINORLINEWIDTH = 0.004
    COMPASS_DISK_RESOLUTION = 10
    COMPASS_SEPARATE_DISK_RESOLUTION = 5
    COMPASS_DISK_MARKERWIDTH = 0.2
    COMPASS_DISK_MARKERHEIGHT = 0.133
    UNKNOWN_BATTERY = -1
    UNKNOWN_ATTITUDE = 0
    UNKNOWN_ALTITUDE = -1000
    UNKNOWN_SPEED = -1
    UNKNOWN_COUNT = -1
    UNKNOWN_GPSFIXTYPE = -1

    TAPE_GAUGES_TICKWIDTH_MAJOR = 0.25
    TAPE_GAUGES_TICKWIDTH_MINOR = 0.15

    # The altitude difference between top and bottom of scale
    ALTIMETER_LINEAR_SPAN = 50
    # every 5 meters there is a tick mark
    ALTIMETER_LINEAR_RESOLUTION = 5
    # every 10 meters there is a number
    ALTIMETER_LINEAR_MAJOR_RESOLUTION = 10

    ALTIMETER_VVI_SPAN = 5
    ALTIMETER_VVI_WIDTH = 0.2
    AIRSPEED_LINEAR_SPAN = 15
    AIRSPEED_LINEAR_RESOLUTION = 1
    AIRSPEED_LINEAR_MAJOR_RESOLUTION = 5

    tickValues = [10, 20, 30, 45, 60]
    compassWindNames = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    visibilityChanged = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.instrumentOpagueBackground = QBrush(QColor.fromHsvF(0, 0, 0.3, 1.0))
        self.instrumentBackground = QBrush(QColor.fromHsvF(0, 0, 0.3, 0.3))
        self.instrumentEdgePen = QPen(QColor.fromHsvF(0, 0, 0.65, 0.5))
        self.font = QFont()
        self.lineWidth = 2
        self.fineLineWidth = 1

        self.navigationTargetBearing = PrimaryFlightDisplay.UNKNOWN_ATTITUDE
        self.navigationCrosstrackError = 0
        self.primaryAltitude = PrimaryFlightDisplay.UNKNOWN_ALTITUDE
        self.GPSAltitude = PrimaryFlightDisplay.UNKNOWN_ALTITUDE
        self.verticalVelocity = PrimaryFlightDisplay.UNKNOWN_ALTITUDE
        self.primarySpeed = PrimaryFlightDisplay.UNKNOWN_SPEED
        self.groundspeed = PrimaryFlightDisplay.UNKNOWN_SPEED
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.rollspeed = 0.0
        self.pitchspeed = 0.0
        self.yawspeed = 0.0
        self.latitude = 0.0
        self.longitude = 0.0
        self.additionalParameters = {}

        self.param = UserData.getInstance().getUserDataEntry(UD_PFD_KEY, {})
        self.isGPSSpeedPrimary = UserData.getParameterValue(self.param, UD_PFD_PRIMARY_SPEED_SOURCE_KEY) == 'GPS'
        self.isGPSAltitudePrimary = UserData.getParameterValue(self.param, UD_PFD_PRIMARY_ALTITUDE_SOURCE_KEY) == 'GPS'
        self.setMinimumSize(480, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.smallTestSize = self.SMALL_TEXT_SIZE
        self.mediumTextSize = self.MEDIUM_TEXT_SIZE
        self.largeTextSize = self.LARGE_TEXT_SIZE
        self.uiTimer = QTimer(self)
        self.uiTimer.setInterval(40)
        self.uiTimer.timeout.connect(self.update)
        self.uas = None

    def setActiveUAS(self, uas):
        uas.updateAttitudeSignal.connect(self.updateAttitude)
        uas.updateBatterySignal.connect(self.updateBatteryStatus)
        uas.updateGlobalPositionSignal.connect(self.updateGlobalPosition)
        uas.updateAirSpeedSignal.connect(self.updatePrimarySpeed)
        uas.updateGroundSpeedSignal.connect(self.updateGPSSpeed)
        uas.updateGPSStatusSignal.connect(self.updateGPSReception)
        uas.updateRCStatusSignal.connect(self.updateRCStatus)
        self.uas = uas

    def updateRCStatus(self, sourceUAS, rcType, rssi, noise, errors):
        unused(sourceUAS, rcType)
        self.additionalParameters['rc_rssi'] = rssi
        self.additionalParameters['rc_noise'] = noise
        self.additionalParameters['rc_errors'] = errors

    def updateAttitude(self, sourceUAS, timestamp, roll, pitch, yaw):
        scale = 180 / math.pi
        self.pitch = self.pitch if math.isnan(pitch) else pitch * scale
        self.roll = self.roll if math.isnan(roll) else roll * scale
        self.yaw = self.yaw if math.isnan(yaw) else yaw * scale
        unused(sourceUAS, timestamp)

    def updateAttitudeSpeed(self, sourceUAS, timestamp, rollspeed, pitchspeed, yawspeed):
        scale = 180 / math.pi
        self.rollspeed = self.rollspeed if math.isnan(rollspeed) else rollspeed * scale
        self.pitchspeed = self.pitchspeed if math.isnan(pitchspeed) else pitchspeed * scale
        self.yawspeed = self.yawspeed if math.isnan(yawspeed) else yawspeed * scale
        unused(sourceUAS, timestamp)

    def updateGlobalPosition(self, sourceUAS, timestamp, latitude, longitude, altitude):
        self.latitude = self.latitude if math.isnan(latitude) else latitude
        self.longitude = self.longitude if math.isnan(longitude) else longitude
        self.GPSAltitude = self.GPSAltitude if math.isnan(altitude) else altitude
        unused(sourceUAS, timestamp)

    def updatePrimaryAltitude(self, sourceUAS, timestamp, altitude):
        self.primaryAltitude = self.primaryAltitude if math.isnan(altitude) else altitude
        unused(sourceUAS, timestamp)

    def updateGPSAltitude(self, sourceUAS, timestamp, altitude):
        self.GPSAltitude = self.GPSAltitude if math.isnan(altitude) else altitude
        unused(sourceUAS, timestamp)

    def updatePrimarySpeed(self, sourceUAS, timestamp, speed):
        self.primarySpeed = self.primarySpeed if math.isnan(speed) else speed
        unused(sourceUAS, timestamp)

    def updateBatteryStatus(self, sourceUAS, timestamp, voltage, current, remaining):
        self.additionalParameters['voltage'] = voltage
        self.additionalParameters['current'] = current
        self.additionalParameters['remaining'] = remaining
        unused(sourceUAS, timestamp)

    def updateGPSReception(self, sourceUAS, timestamp, fixType, hdop, vdop, satelliteCount, hacc, vacc, velacc, hdgacc):
        self.additionalParameters['gps_fix'] = fixType
        self.additionalParameters['gps_satellite'] = satelliteCount
        unused(sourceUAS, timestamp, hdop, vdop, hacc, vacc, velacc, hdgacc)

    def updateGPSSpeed(self, sourceUAS, timestamp, speed):
        self.groundspeed = self.groundspeed if math.isnan(speed) else speed
        unused(sourceUAS, timestamp)

    def paintEvent(self, event):
        unused(event)
        compassAIIntrusion = 0
        compassHalfSpan = 180
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.HighQualityAntialiasing, True)

        tapeGaugeWidth = self.tapesGaugeWidthFor(self.width(), self.width())
        aiheight = self.height()
        aiwidth = self.width() - tapeGaugeWidth * 2
        if (aiheight > aiwidth):
            aiheight = aiwidth
        AIMainArea = QRectF(tapeGaugeWidth, 0, aiwidth, aiheight)
        AIPaintArea = QRectF(0, 0, self.width(), self.height())

        velocityMeterArea = QRectF(0, 0, tapeGaugeWidth, aiheight)
        altimeterArea = QRectF(AIMainArea.right(), 0, tapeGaugeWidth, aiheight)

        # calc starts
        compassRelativeWidth = 0.75
        compassBottomMargin = 0.78
        compassSize = compassRelativeWidth  * AIMainArea.width() # Diameter is this times the width.
        compassCenterY = AIMainArea.bottom() + compassSize / 4

        if self.height() - compassCenterY > AIMainArea.width() / 2 * compassBottomMargin:
            compassCenterY = self.height()-AIMainArea.width()/2*compassBottomMargin
        compassCenterY = (compassCenterY * 2 + AIMainArea.bottom() + compassSize / 4) / 3

        compassArea = QRectF(AIMainArea.x()+(1-compassRelativeWidth)/2*AIMainArea.width(),
                             compassCenterY-compassSize/2, compassSize, compassSize)

        if self.height()-compassCenterY < compassSize/2:
            compassHalfSpan = math.acos((compassCenterY-self.height())*2/compassSize) * 180/math.pi + self.COMPASS_DISK_RESOLUTION
            if compassHalfSpan > 180:
                compassHalfSpan = 180

        compassAIIntrusion = compassSize / 2 + AIMainArea.bottom() - compassCenterY
        if compassAIIntrusion < 0:
            compassAIIntrusion = 0
        #calc ends

        hadClip = painter.hasClipping()

        painter.setClipping(True)
        painter.setClipRect(AIPaintArea)

        self.drawAIGlobalFeatures(painter, AIMainArea, AIPaintArea)
        self.drawAIAttitudeScales(painter, AIMainArea, compassAIIntrusion)
        self.drawAIAirframeFixedFeatures(painter, AIMainArea)
        self.drawAICompassDisk(painter, compassArea, compassHalfSpan)

        painter.setClipping(hadClip)
        if self.isGPSAltitudePrimary:
            self.drawAltimeter(painter, altimeterArea, self.GPSAltitude, self.primaryAltitude, self.verticalVelocity)
        else:
            self.drawAltimeter(painter, altimeterArea, self.primaryAltitude, self.GPSAltitude, self.verticalVelocity)
        if self.isGPSSpeedPrimary:
            self.drawVelocityMeter(painter, velocityMeterArea, self.groundspeed, self.primarySpeed)
        else:
            self.drawVelocityMeter(painter, velocityMeterArea, self.primarySpeed, self.groundspeed)
        painter.end()

    def showEvent(self, event):
        super().showEvent(event)
        self.uiTimer.start()
        self.visibilityChanged.emit(True)

    def hideEvent(self, event):
        self.uiTimer.stop()
        super().hideEvent(event)
        self.visibilityChanged.emit(False)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        size = e.size().width()
        self.lineWidth = self.constrain(size * self.LINEWIDTH, 1, 6)
        self.fineLineWidth = self.constrain(size * self.LINEWIDTH * 2 / 3, 1, 2)
        self.instrumentEdgePen.setWidthF(self.fineLineWidth)
        self.smallTestSize = size * self.SMALL_TEXT_SIZE
        self.mediumTextSize = size * self.MEDIUM_TEXT_SIZE
        self.largeTextSize = size * self.LARGE_TEXT_SIZE

    def drawTextCenter(self, painter, text, pixelSize, x, y):
        self.font.setPixelSize(pixelSize)
        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)
        bounds = metrics.boundingRect(text)
        painter.drawText(x - bounds.width() / 2, y - bounds.height() / 2, bounds.width(), bounds.height(), Qt.AlignCenter | Qt.TextDontClip, text)

    def drawTextLeftCenter(self, painter, text, pixelSize, x, y):
        self.font.setPixelSize(pixelSize)
        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)
        bounds = metrics.boundingRect(text)
        painter.drawText(x , y - bounds.height() / 2, bounds.width(), bounds.height(), Qt.AlignLeft | Qt.TextDontClip, text)

    def drawTextRightCenter(self, painter, text, pixelSize, x, y):
        self.font.setPixelSize(pixelSize)
        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)
        bounds = metrics.boundingRect(text)
        painter.drawText(x - bounds.width(), y - bounds.height() / 2, bounds.width(), bounds.height(), Qt.AlignRight | Qt.TextDontClip, text)

    def drawTextCenterTop(self, painter, text, pixelSize, x, y):
        self.font.setPixelSize(pixelSize)
        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)
        bounds = metrics.boundingRect(text)
        painter.drawText(x - bounds.width() / 2, y + bounds.height(), bounds.width(), bounds.height(), Qt.AlignCenter | Qt.TextDontClip, text)

    def drawTextCenterBottom(self, painter, text, pixelSize, x, y):
        self.font.setPixelSize(pixelSize)
        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)
        bounds = metrics.boundingRect(text)
        painter.drawText(x - bounds.width() / 2, y, bounds.width(), bounds.height(), Qt.AlignCenter, text)

    def drawInstrumentBackground(self, painter, edge):
        painter.setPen(self.instrumentEdgePen)
        painter.drawRect(edge)

    def fillInstrumentBackground(self, painter, edge):
        painter.setPen(self.instrumentEdgePen)
        painter.setBrush(self.instrumentBackground)
        painter.drawRect(edge)
        painter.setBrush(Qt.NoBrush)

    def fillInstrumentOpagueBackground(self, painter, edge):
        painter.setPen(self.instrumentEdgePen)
        painter.setBrush(self.instrumentOpagueBackground)
        painter.drawRect(edge)
        painter.setBrush(Qt.NoBrush)

    def constrain(self, value, mn, mx):
        if value < mn:
            value = mn
        elif value > mx:
            value = mx
        return value

    def pitchAngleToTranslation(self, viewHeight, pitch):
        return pitch * viewHeight / 65.0 #PITCHTRANSLATION

    def tapesGaugeWidthFor(self, containerWidth, preferredAIWidth):
        result = (containerWidth - preferredAIWidth) / 2.0
        minimum = containerWidth / 5.5
        if result < minimum:
            result = minimum
        return result

    def min4(self, a, b, c, d):
        if b < a:
            a = b
        if c < a:
            a = c
        if d < a:
            a = d
        return a

    def max4(self, a, b, c, d):
        if b > a:
            a = b
        if c > a:
            a = c
        if d > a:
            a = d
        return a

    def drawAIAttitudeScales(self, painter, area, intrusion):
        # To save computations, we do these transformations once for both scales:
        painter.resetTransform()
        painter.translate(area.center())
        painter.rotate(-self.roll)
        saved = painter.transform()

        self.drawRollScale(painter, area, True, True)
        painter.setTransform(saved)
        self.drawPitchScale(painter, area, intrusion, True, True)

    def drawPitchScale(self, painter, area, intrusion, drawNumbersLeft, drawNumbersRight):
        unused(intrusion)
        # The area should be quadratic but if not width is the major size.
        w = area.width()
        if w < area.height():
            w = area.height()

        pen = QPen()
        pen.setWidthF(self.lineWidth)
        pen.setColor(Qt.white)
        painter.setPen(pen)

        savedTransform = painter.transform()

        # find the mark nearest center
        snap = qRound(self.pitch / self.PITCH_SCALE_RESOLUTION) * self.PITCH_SCALE_RESOLUTION
        _min = snap-self.PITCH_SCALE_HALFRANGE
        _max = snap+self.PITCH_SCALE_HALFRANGE
        degrees = _min
        while degrees <= _max:
            isMajor = degrees % (self.PITCH_SCALE_RESOLUTION * 2) == 0
            linewidth = self.PITCH_SCALE_MINORWIDTH
            if isMajor:
                linewidth = self.PITCH_SCALE_MAJORWIDTH
            if abs(degrees) > self.PITCH_SCALE_WIDTHREDUCTION_FROM:
                # we want: 1 at PITCH_SCALE_WIDTHREDUCTION_FROM and PITCH_SCALE_WIDTHREDUCTION at 90.
                # That is PITCH_SCALE_WIDTHREDUCTION + (1-PITCH_SCALE_WIDTHREDUCTION) * f(pitch)
                # where f(90)=0 and f(PITCH_SCALE_WIDTHREDUCTION_FROM)=1
                # f(p) = (90-p) * 1/(90-PITCH_SCALE_WIDTHREDUCTION_FROM)
                # or PITCH_SCALE_WIDTHREDUCTION + f(pitch) - f(pitch) * PITCH_SCALE_WIDTHREDUCTION
                # or PITCH_SCALE_WIDTHREDUCTION (1-f(pitch)) + f(pitch)
                fromVertical = -90-self.pitch
                if self.pitch >= 0:
                    fromVertical = 90-self.pitch
                if fromVertical < 0:
                    fromVertical = -fromVertical
                temp = fromVertical * 1/(90.0-self.PITCH_SCALE_WIDTHREDUCTION_FROM)
                linewidth *= (self.PITCH_SCALE_WIDTHREDUCTION * (1-temp) + temp)
            shift = self.pitchAngleToTranslation(w, self.pitch - degrees)

            # TODO: Intrusion detection and evasion. That is, don't draw
            # where the compass has intruded.
            painter.translate(0, shift)
            start = QPointF(-linewidth*w, 0)
            end = QPointF(linewidth*w, 0)
            painter.drawLine(start, end)

            if isMajor and (drawNumbersLeft or drawNumbersRight):
                displayDegrees = degrees
                if displayDegrees > 90:
                    displayDegrees = 180 - displayDegrees
                elif displayDegrees < -90:
                    displayDegrees = -180 - displayDegrees
                if self.SHOW_ZERO_ON_SCALES or degrees:
                    if drawNumbersLeft:
                        self.drawTextRightCenter(painter, '{0}'.format(displayDegrees), self.mediumTextSize, -self.PITCH_SCALE_MAJORWIDTH * w-10, 0)
                    if drawNumbersRight:
                        self.drawTextLeftCenter(painter, '{0}'.format(displayDegrees), self.mediumTextSize, self.PITCH_SCALE_MAJORWIDTH * w+10, 0)

            painter.setTransform(savedTransform)
            degrees += self.PITCH_SCALE_RESOLUTION

    def drawRollScale(self, painter, area, drawTicks, drawNumbers):
        w = area.width()
        if w < area.height():
            w = area.height()

        pen = QPen()
        pen.setWidthF(self.lineWidth)
        pen.setColor(Qt.white)
        painter.setPen(pen)

        # We should really do these transforms but they are assumed done by caller.
        # painter.resetTransform()
        # painter.translate(area.center())
        # painter.rotate(roll)

        _size = w * self.ROLL_SCALE_RADIUS*2
        arcArea = QRectF(-_size/2, - _size/2, _size, _size)
        painter.drawArc(arcArea, (90-self.ROLL_SCALE_RANGE)*16, self.ROLL_SCALE_RANGE*2*16)
        # painter.drawEllipse(QPoint(0,0),200,200)
        if drawTicks:
            length = len(self.tickValues)
            previousRotation = 0
            i = 0
            while i <length*2+1:
                degrees = 0
                if i > length:
                    degrees = -self.tickValues[i-length-1]
                elif i < length:
                    degrees =  self.tickValues[i]
                #degrees = 180 - degrees
                painter.rotate(degrees - previousRotation)
                previousRotation = degrees

                start = QPointF(0, -_size/2)
                end = QPointF(0, -(1.0+self.ROLL_SCALE_TICKMARKLENGTH)*_size/2)

                painter.drawLine(start, end)

                #QString s_number # = QString("%d").arg(degrees);
                #if (SHOW_ZERO_ON_SCALES || degrees)
                #    s_number.sprintf("%d", abs(degrees));

                if drawNumbers:
                    self.drawTextCenterBottom(painter, '{0}'.format(abs(degrees)), self.mediumTextSize, 0, -(self.ROLL_SCALE_RADIUS+self.ROLL_SCALE_TICKMARKLENGTH*1.7)*w)
                i = i + 1

    def drawAIAirframeFixedFeatures(self, painter, area):
        '''
        red line from -7/10 to -5/10 half-width
        red line from 7/10 to 5/10 half-width
        red slanted line from -2/10 half-width to 0
        red slanted line from 2/10 half-width to 0
        red arrow thing under roll scale
        prepareTransform(painter, width, height);
        '''
        painter.resetTransform()
        painter.translate(area.center())

        w = area.width()
        h = area.height()

        pen = QPen()
        pen.setWidthF(self.lineWidth * 1.5)
        pen.setColor(QColor(255, 0, 0))
        painter.setPen(pen)

        length = 0.15
        side = 0.5
        # The 2 lines at sides.
        painter.drawLine(QPointF(-side*w, 0), QPointF(-(side-length)*w, 0))
        painter.drawLine(QPointF(side*w, 0), QPointF((side-length)*w, 0))

        pen.setColor(QColor(255, 255, 255))
        painter.setPen(pen)
        v = abs(self.__getAdditionalParameter('voltage'))
        a = abs(self.__getAdditionalParameter('current'))
        # Power usage
        self.drawTextLeftCenter(painter, '{:.1f}V'.format(v), self.smallTestSize, -side*w*0.9, side*w/4)
        self.drawTextLeftCenter(painter, '{:.1f}A'.format(a), self.smallTestSize, -side*w*0.9, side*w/4 + self.mediumTextSize * 1.1)
        # GPS groundspeed / IAS
        spd = ''
        if self.isGPSSpeedPrimary:
            # TODO add option to hide air speed when there is no air speed sensor
            spd = 'IAS ---' if self.primarySpeed == self.UNKNOWN_SPEED else 'IAS {:.1f}'.format(self.primarySpeed)
        else:
            spd = 'GS ---' if self.groundspeed == self.UNKNOWN_SPEED else 'GS {:.1f}'.format(self.groundspeed)
        self.drawTextLeftCenter(painter, spd, self.smallTestSize, -side*w*0.9, side*w/4 + self.mediumTextSize * 3.3)
        # Number of GPS satellites
        s = self.__getAdditionalParameter('gps_satellite')
        s = 0 if s == 255 else s
        self.drawTextRightCenter(painter, '{} {}'.format(chr(0x1F6F0), s), self.smallTestSize, side*w*0.9, side*w/4)
        # RC receiver RSSI
        s = self.__getAdditionalParameter('rc_rssi')
        s = 0 if s == 255 else s
        s /= 254.0
        self.drawTextRightCenter(painter, '{} {}'.format(chr(0x1F4F6), int(s * 100.0)), self.smallTestSize, side*w*0.9, side*w/4 + self.smallTestSize * 1.5)

        pen.setColor(QColor(255, 0, 0))
        painter.setPen(pen)
        rel = length / math.sqrt(2)
        # The gull
        painter.drawLine(QPointF(rel*w, rel*w/2), QPoint(0, 0))
        painter.drawLine(QPointF(-rel*w, rel*w/2), QPoint(0, 0))

        # The roll scale marker.
        markerPath = QPainterPath(QPointF(0, -w*self.ROLL_SCALE_RADIUS+1))
        markerPath.lineTo(-h*self.ROLL_SCALE_MARKERWIDTH/2, -w*(self.ROLL_SCALE_RADIUS-self.ROLL_SCALE_MARKERHEIGHT)+1)
        markerPath.lineTo(h*self.ROLL_SCALE_MARKERWIDTH/2, -w*(self.ROLL_SCALE_RADIUS-self.ROLL_SCALE_MARKERHEIGHT)+1)
        markerPath.closeSubpath()
        painter.drawPath(markerPath)

    def drawAIGlobalFeatures(self, painter, mainArea, paintArea):
        painter.resetTransform()
        painter.translate(mainArea.center())

        pitchPixels = self.pitchAngleToTranslation(mainArea.height(), self.pitch)
        gradientEnd = self.pitchAngleToTranslation(mainArea.height(), 60)

        if math.isnan(self.roll) == False: # check for NaN
            painter.rotate(-self.roll)
        painter.translate(0, pitchPixels)

        # Calculate the radius of area we need to paint to cover all.
        rtx = painter.transform().inverted()[0]

        topLeft = rtx.map(paintArea.topLeft())
        topRight = rtx.map(paintArea.topRight())
        bottomLeft = rtx.map(paintArea.bottomLeft())
        bottomRight = rtx.map(paintArea.bottomRight())
        # Just KISS... make a rectangluar basis.
        minx = self.min4(topLeft.x(), topRight.x(), bottomLeft.x(), bottomRight.x())
        maxx = self.max4(topLeft.x(), topRight.x(), bottomLeft.x(), bottomRight.x())
        miny = self.min4(topLeft.y(), topRight.y(), bottomLeft.y(), bottomRight.y())
        maxy = self.max4(topLeft.y(), topRight.y(), bottomLeft.y(), bottomRight.y())

        hzonLeft = QPoint(minx, 0)
        hzonRight = QPoint(maxx, 0)

        skyPath = QPainterPath(hzonLeft)
        skyPath.lineTo(QPointF(minx, miny))
        skyPath.lineTo(QPointF(maxx, miny))
        skyPath.lineTo(hzonRight)
        skyPath.closeSubpath()

        # TODO: The gradient is wrong now.
        skyGradient = QLinearGradient(0, -gradientEnd, 0, 0)
        skyGradient.setColorAt(0, QColor.fromHsvF(0.6, 1.0, 0.7))
        skyGradient.setColorAt(1, QColor.fromHsvF(0.6, 0.25, 0.9))
        skyBrush = QBrush(skyGradient)
        painter.fillPath(skyPath, skyBrush)

        groundPath = QPainterPath(hzonRight)
        groundPath.lineTo(maxx, maxy)
        groundPath.lineTo(minx, maxy)
        groundPath.lineTo(hzonLeft)
        groundPath.closeSubpath()

        groundGradient = QLinearGradient(0, gradientEnd, 0, 0)
        groundGradient.setColorAt(0, QColor.fromHsvF(0.25, 1, 0.5))
        groundGradient.setColorAt(1, QColor.fromHsvF(0.25, 0.25, 0.5))
        groundBrush = QBrush(groundGradient)
        painter.fillPath(groundPath, groundBrush)

        pen = QPen()
        pen.setWidthF(self.lineWidth)
        pen.setColor(QColor(0, 255, 0))
        painter.setPen(pen)

        start = QPointF(-mainArea.width(), 0)
        end = QPoint(mainArea.width(), 0)
        painter.drawLine(start, end)

    def drawAICompassDisk(self, painter, area, halfspan):
        start = self.yaw - halfspan
        end = self.yaw + halfspan

        firstTick = math.ceil(start / self.COMPASS_DISK_RESOLUTION) * self.COMPASS_DISK_RESOLUTION
        lastTick = math.floor(end / self.COMPASS_DISK_RESOLUTION) * self.COMPASS_DISK_RESOLUTION

        radius = area.width()/2
        innerRadius = radius * 0.96
        painter.resetTransform()
        painter.setBrush(self.instrumentBackground)
        painter.setPen(self.instrumentEdgePen)
        painter.drawEllipse(area)
        painter.setBrush(Qt.NoBrush)

        scalePen = QPen(Qt.black)
        scalePen.setWidthF(self.fineLineWidth)

        tickYaw = firstTick
        while tickYaw <= lastTick:
            displayTick = tickYaw
            if displayTick < 0:
                displayTick += 360
            elif displayTick >= 360:
                displayTick -= 360

            # yaw is in center.
            off = tickYaw - self.yaw
            # wrap that to ]-180..180]
            if off <= -180:
                off += 360
            elif off > 180:
                off -= 360

            painter.translate(area.center())
            painter.rotate(off)
            drewArrow = False
            isMajor = displayTick % self.COMPASS_DISK_MAJORTICK == 0

            if displayTick == 30 or displayTick == 60 or \
               displayTick ==120 or displayTick ==150 or \
               displayTick ==210 or displayTick ==240 or \
               displayTick ==300 or displayTick ==330:
                # draw a number
                painter.setPen(scalePen)
                self.drawTextCenter(painter, '{0}'.format(int(displayTick / 10)), self.smallTestSize, 0, -innerRadius*0.75)
            else:
                if displayTick % self.COMPASS_DISK_ARROWTICK == 0:
                    if displayTick != 0:
                        markerPath = QPainterPath(QPointF(0, -innerRadius*(1-self.COMPASS_DISK_MARKERHEIGHT/2)))
                        markerPath.lineTo(innerRadius*self.COMPASS_DISK_MARKERWIDTH/4, -innerRadius)
                        markerPath.lineTo(-innerRadius*self.COMPASS_DISK_MARKERWIDTH/4, -innerRadius)
                        markerPath.closeSubpath()
                        painter.setPen(scalePen)
                        painter.setBrush(Qt.SolidPattern)
                        painter.drawPath(markerPath)
                        painter.setBrush(Qt.NoBrush)
                        drewArrow = True
                    if displayTick%90 == 0:
                        # Also draw a label
                        name = self.compassWindNames[qRound(displayTick / 45)]
                        painter.setPen(scalePen)
                        self.drawTextCenter(painter, name, self.mediumTextSize, 0, -innerRadius*0.75)

            # draw the scale lines. If an arrow was drawn, stay off from it.
            if drewArrow:
                p_start = QPoint(0, -innerRadius*0.94)
            else:
                p_start = QPoint(0, -innerRadius)
            if isMajor:
                p_end = QPoint(0, -innerRadius*0.86)
            else:
                p_end = QPoint(0, -innerRadius*0.90)

            painter.setPen(scalePen)
            painter.drawLine(p_start, p_end)
            painter.resetTransform()
            tickYaw += self.COMPASS_DISK_RESOLUTION

        painter.setPen(scalePen)
        painter.translate(area.center())
        markerPath = QPainterPath(QPointF(0, -radius-2))
        markerPath.lineTo(radius*self.COMPASS_DISK_MARKERWIDTH/2,  -radius-radius*self.COMPASS_DISK_MARKERHEIGHT-2)
        markerPath.lineTo(-radius*self.COMPASS_DISK_MARKERWIDTH/2, -radius-radius*self.COMPASS_DISK_MARKERHEIGHT-2)
        markerPath.closeSubpath()
        painter.drawPath(markerPath)

        digitalCompassYCenter = -radius * 0.52
        digitalCompassHeight = radius * 0.28

        digitalCompassBottom = QPointF(0, digitalCompassYCenter+digitalCompassHeight)
        digitalCompassAbsoluteBottom = painter.transform().map(digitalCompassBottom)

        digitalCompassUpshift = 0
        if digitalCompassAbsoluteBottom.y() > self.height():
            digitalCompassUpshift = digitalCompassAbsoluteBottom.y() - self.height()

        digitalCompassRect = QRectF(-radius/3, -radius*0.52-digitalCompassUpshift, radius*2/3, radius*0.28)
        painter.setPen(self.instrumentEdgePen)
        painter.drawRoundedRect(digitalCompassRect, self.instrumentEdgePen.widthF()*2/3, self.instrumentEdgePen.widthF()*2/3)

        # final safeguard for really stupid systems 
        digitalCompassValue = qRound(self.yaw) % 360

        pen = QPen()
        pen.setWidthF(self.lineWidth)
        pen.setColor(Qt.white)
        painter.setPen(pen)

        self.drawTextCenter(painter, '%03d' % digitalCompassValue, self.largeTextSize, 0, -radius*0.38-digitalCompassUpshift)

        # The CDI
        if self.shouldDisplayNavigationData() and self.navigationTargetBearing != self.UNKNOWN_ATTITUDE and not math.isinf(self.navigationCrosstrackError):
            painter.resetTransform()
            painter.translate(area.center())
            # TODO : Sign might be wrong?
            # TODO : The case where error exceeds max. Truncate to max. and make that visible somehow.
            # bool errorBeyondRadius = false
            if abs(self.navigationCrosstrackError) > self.CROSSTRACK_MAX:
                #errorBeyondRadius = true
                if self.navigationCrosstrackError > 0:
                    self.navigationCrosstrackError = self.CROSSTRACK_MAX
                else:
                    self.navigationCrosstrackError = -self.CROSSTRACK_MAX

            r = radius * self.CROSSTRACK_RADIUS
            x = self.navigationCrosstrackError / self.CROSSTRACK_MAX * r
            y = math.sqrt(r*r - x*x) # the positive y, there is also a negative.

            sillyHeading = 0
            angle = sillyHeading - self.navigationTargetBearing # TODO: sign.
            painter.rotate(-angle)

            pen = QPen()
            pen.setWidthF(self.lineWidth)
            pen.setColor(Qt.black)
            painter.setPen(pen)
            painter.drawLine(QPointF(x, y), QPointF(x, -y))

    def drawAltimeter(self, painter, area, primaryAltitude, secondaryAltitude, vv):
        unused(secondaryAltitude)
        painter.resetTransform()
        self.fillInstrumentBackground(painter, area)

        pen = QPen()
        pen.setWidthF(self.lineWidth)
        pen.setColor(Qt.white)
        painter.setPen(pen)

        h = area.height()
        w = area.width()
        #float secondaryAltitudeBoxHeight = mediumTextSize * 2;
        # The height where we being with new tickmarks.
        effectiveHalfHeight = h * 0.45

        # not yet implemented: Display of secondary altitude.
        # if (isAirplane())
        #    effectiveHalfHeight-= secondaryAltitudeBoxHeight;

        markerHalfHeight = self.mediumTextSize*0.8
        leftEdge = self.instrumentEdgePen.widthF()*2
        rightEdge = w-leftEdge
        tickmarkLeft = leftEdge
        tickmarkRightMajor = tickmarkLeft+self.TAPE_GAUGES_TICKWIDTH_MAJOR*w
        tickmarkRightMinor = tickmarkLeft+self.TAPE_GAUGES_TICKWIDTH_MINOR*w
        numbersLeft = 0.42*w
        markerTip = (tickmarkLeft*2+tickmarkRightMajor)/3
        scaleCenterAltitude = 0 if primaryAltitude == self.UNKNOWN_ALTITUDE else primaryAltitude

        # altitude scale
        start = scaleCenterAltitude - self.ALTIMETER_LINEAR_SPAN/2
        end = scaleCenterAltitude + self.ALTIMETER_LINEAR_SPAN/2
        firstTick = math.ceil(start / self.ALTIMETER_LINEAR_RESOLUTION) * self.ALTIMETER_LINEAR_RESOLUTION
        lastTick = math.floor(end / self.ALTIMETER_LINEAR_RESOLUTION) * self.ALTIMETER_LINEAR_RESOLUTION
        tickAlt = firstTick
        while tickAlt <= lastTick:
            y = (tickAlt-scaleCenterAltitude)*effectiveHalfHeight/(self.ALTIMETER_LINEAR_SPAN/2)
            isMajor = tickAlt % self.ALTIMETER_LINEAR_MAJOR_RESOLUTION == 0
            painter.resetTransform()
            painter.translate(area.left(), area.center().y() - y)
            pen.setColor(Qt.red if tickAlt < 0 else Qt.white)
            painter.setPen(pen)
            if isMajor:
                painter.drawLine(tickmarkLeft, 0, tickmarkRightMajor, 0)
                self.drawTextLeftCenter(painter, '{0}'.format(abs(tickAlt)), self.mediumTextSize, numbersLeft, 0)
            else:
                painter.drawLine(tickmarkLeft, 0, tickmarkRightMinor, 0)
            tickAlt += self.ALTIMETER_LINEAR_RESOLUTION

        markerPath = QPainterPath(QPoint(markerTip, 0))
        markerPath.lineTo(markerTip+markerHalfHeight, markerHalfHeight)
        markerPath.lineTo(rightEdge, markerHalfHeight)
        markerPath.lineTo(rightEdge, -markerHalfHeight)
        markerPath.lineTo(markerTip+markerHalfHeight, -markerHalfHeight)
        markerPath.closeSubpath()

        painter.resetTransform()
        painter.translate(area.left(), area.center().y())

        pen.setWidthF(self.lineWidth)
        pen.setColor(Qt.white)
        painter.setPen(pen)

        painter.setBrush(Qt.SolidPattern)
        painter.drawPath(markerPath)
        painter.setBrush(Qt.NoBrush)

        pen.setColor(Qt.white)
        painter.setPen(pen)

        xCenter = (markerTip+rightEdge)/2
        alttxt = '---' if primaryAltitude == self.UNKNOWN_ALTITUDE else '%3.0f' % primaryAltitude
        self.drawTextCenter(painter, alttxt, self.mediumTextSize, xCenter, 0)

        if vv == self.UNKNOWN_ALTITUDE:
            return
        vvPixHeight = -vv / self.ALTIMETER_VVI_SPAN * effectiveHalfHeight
        if abs(vvPixHeight) < markerHalfHeight:
            return # hidden behind marker.

        vvSign = -1
        if vvPixHeight > 0:
            vvSign = 1

        # QRectF vvRect(rightEdge - w*ALTIMETER_VVI_WIDTH, markerHalfHeight*vvSign, w*ALTIMETER_VVI_WIDTH, abs(vvPixHeight)*vvSign);
        vvArrowBegin = QPointF(rightEdge - w*self.ALTIMETER_VVI_WIDTH/2, markerHalfHeight*vvSign)
        vvArrowEnd = QPointF(rightEdge - w*self.ALTIMETER_VVI_WIDTH/2, vvPixHeight)
        painter.drawLine(vvArrowBegin, vvArrowEnd)

        # Yeah this is a repitition of above code but we are goigd to trash it all anyway, so no fix.
        vvArowHeadSize = abs(vvPixHeight - markerHalfHeight*vvSign)
        if vvArowHeadSize > w*self.ALTIMETER_VVI_WIDTH/3:
            vvArowHeadSize = w*self.ALTIMETER_VVI_WIDTH/3

        xcenter = rightEdge-w*self.ALTIMETER_VVI_WIDTH/2

        vvArrowHead = QPointF(xcenter+vvArowHeadSize, vvPixHeight - vvSign *vvArowHeadSize)
        painter.drawLine(vvArrowHead, vvArrowEnd)

        vvArrowHead = QPointF(xcenter-vvArowHeadSize, vvPixHeight - vvSign * vvArowHeadSize)
        painter.drawLine(vvArrowHead, vvArrowEnd)

    def drawVelocityMeter(self, painter, area, speed, secondarySpeed):
        unused(secondarySpeed)
        painter.resetTransform()
        self.fillInstrumentBackground(painter, area)

        pen = QPen()
        pen.setWidthF(self.lineWidth)

        h = area.height()
        w = area.width()
        effectiveHalfHeight = h*0.45
        markerHalfHeight = self.mediumTextSize
        leftEdge = self.instrumentEdgePen.widthF()*2
        tickmarkRight = w-leftEdge
        tickmarkLeftMajor = tickmarkRight-w*self.TAPE_GAUGES_TICKWIDTH_MAJOR
        tickmarkLeftMinor = tickmarkRight-w*self.TAPE_GAUGES_TICKWIDTH_MINOR
        numbersRight = 0.42*w
        markerTip = (tickmarkLeftMajor+tickmarkRight*2)/3

        # Select between air and ground speed:
        centerScaleSpeed = 0 if speed == self.UNKNOWN_SPEED else speed
        start = centerScaleSpeed - self.AIRSPEED_LINEAR_SPAN/2
        end = centerScaleSpeed +self. AIRSPEED_LINEAR_SPAN/2

        firstTick = math.ceil(start / self.AIRSPEED_LINEAR_RESOLUTION) * self.AIRSPEED_LINEAR_RESOLUTION
        lastTick = math.floor(end / self.AIRSPEED_LINEAR_RESOLUTION) * self.AIRSPEED_LINEAR_RESOLUTION
        tickSpeed = firstTick
        while tickSpeed <= lastTick:
            if tickSpeed < 0:
                pen.setColor(Qt.red)
            else:
                pen.setColor(Qt.white)
            painter.setPen(pen)

            y = (tickSpeed-centerScaleSpeed)*effectiveHalfHeight/(self.AIRSPEED_LINEAR_SPAN/2)
            hasText = tickSpeed % self.AIRSPEED_LINEAR_MAJOR_RESOLUTION == 0
            painter.resetTransform()
            painter.translate(area.left(), area.center().y() - y)

            if hasText:
                painter.drawLine(tickmarkLeftMajor, 0, tickmarkRight, 0)
                self.drawTextRightCenter(painter, '{0}'.format(abs(tickSpeed)), self.mediumTextSize, numbersRight, 0)
            else:
                painter.drawLine(tickmarkLeftMinor, 0, tickmarkRight, 0)
            tickSpeed += self.AIRSPEED_LINEAR_RESOLUTION

        markerPath = QPainterPath(QPoint(markerTip, 0))
        markerPath.lineTo(markerTip-markerHalfHeight, markerHalfHeight)
        markerPath.lineTo(leftEdge, markerHalfHeight)
        markerPath.lineTo(leftEdge, -markerHalfHeight)
        markerPath.lineTo(markerTip-markerHalfHeight, -markerHalfHeight)
        markerPath.closeSubpath()

        painter.resetTransform()
        painter.translate(area.left(), area.center().y())

        pen.setWidthF(self.lineWidth)
        pen.setColor(Qt.white)
        painter.setPen(pen)
        painter.setBrush(Qt.SolidPattern)
        painter.drawPath(markerPath)
        painter.setBrush(Qt.NoBrush)

        pen.setColor(Qt.white)
        painter.setPen(pen)
        xCenter = (markerTip+leftEdge)/2
        spdtxt = '---' if speed == self.UNKNOWN_SPEED else '%3.1f' % speed
        self.drawTextCenter(painter, spdtxt, self.mediumTextSize, xCenter, 0)

    def shouldDisplayNavigationData(self):
        return True

    def __getAdditionalParameter(self, param, defaultValue = 0):
        if param in self.additionalParameters:
            return self.additionalParameters[param]
        return defaultValue
