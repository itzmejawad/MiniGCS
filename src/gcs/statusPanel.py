import sys

from pymavlink.dialects.v10 import common as mavlink
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QGridLayout, QLabel, QProgressBar,
                             QPushButton, QWidget, QTabWidget, QVBoxLayout)
from compass import Compass
from barometer import Barometer
from plugins.autoquad import AutoQuadControlPanel

GPS_FIX_LABELS = {
    mavlink.GPS_FIX_TYPE_NO_GPS : 'No GPS',
    mavlink.GPS_FIX_TYPE_NO_FIX : 'No fix',
    mavlink.GPS_FIX_TYPE_2D_FIX : '2D fix',
    mavlink.GPS_FIX_TYPE_3D_FIX : '3D fix',
    mavlink.GPS_FIX_TYPE_DGPS : 'DGPS/SBAS aided 3D fix',
    mavlink.GPS_FIX_TYPE_RTK_FLOAT : 'RTK 3D float',
    mavlink.GPS_FIX_TYPE_RTK_FIXED : 'RTK 3D fix',
    mavlink.GPS_FIX_TYPE_STATIC : 'Static fix',
    mavlink.GPS_FIX_TYPE_PPP : 'PPP 3D fix'
}

BATTERY_BAR_STYLE_TEMPLATE = 'QProgressBar::chunk {{background: "{0}"; \
                                                    border: 1px solid black;}}'

class SystemStatusPanel(QWidget):

    connectToMAVLink = pyqtSignal()
    disconnectFromMAVLink = pyqtSignal()
    connectToLocalGPS = pyqtSignal()
    disconnectFromLocalGPS = pyqtSignal()

    apControlPanels = {}

    def __init__(self, parent = None):
        super().__init__(parent)
        self.tabs = QTabWidget(self)
        self.statusPanel = StatusSummaryPanel(self)
        self.tabs.addTab(self.statusPanel, 'Summary')
        self.compassPanel = Compass(self)
        self.tabs.addTab(self.compassPanel, 'Compass')
        self.barometerPanel = Barometer(self)
        self.tabs.addTab(self.barometerPanel, 'Barometer')
        self.apControlPanels[mavlink.MAV_AUTOPILOT_AUTOQUAD] = AutoQuadControlPanel()
        l = QVBoxLayout()
        l.addWidget(self.tabs)
        self.setLayout(l)

    def addAPControlPanel(self, apType):
        if apType in self.apControlPanels:
            t = self.apControlPanels[apType]
            print('Add control panel for AP: {} ({})'.format(t.tabName(), apType))
            self.tabs.addTab(t, t.tabName())
            t.show()
        else:
            print('No control panel available for AP:', apType)

class StatusSummaryPanel(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.connectToMAVLink = parent.connectToMAVLink
        self.disconnectFromMAVLink = parent.disconnectFromMAVLink
        self.connectToLocalGPS = parent.connectToLocalGPS
        self.disconnectFromLocalGPS = parent.disconnectFromLocalGPS
        l = QGridLayout()
        row = 0
        self.sysNameLbl = QLabel('System Status')
        l.addWidget(self.sysNameLbl, row, 0, 1, 3, Qt.AlignLeft)
        row += 1

        self.armedLbl = QLabel('Disarmed')
        self.modeLbl = QLabel('Standby')
        self.gpsLbl = QLabel(GPS_FIX_LABELS[mavlink.GPS_FIX_TYPE_NO_GPS])
        l.addWidget(self.armedLbl, row, 0, 1, 1, Qt.AlignLeft)
        l.addWidget(self.modeLbl, row, 1, 1, 1, Qt.AlignLeft)
        l.addWidget(self.gpsLbl, row, 2, 1, 1, Qt.AlignLeft)
        row += 1

        l.addWidget(QLabel('Battery'), row, 0, 1, 1, Qt.AlignLeft)
        self.battBar = QProgressBar(self)
        self.battBar.setValue(0)
        l.addWidget(self.battBar, row, 1, 1, 1, Qt.AlignLeft)
        self.battVoltLabel = QLabel('0.0V')
        l.addWidget(self.battVoltLabel, row, 2, 1, 1, Qt.AlignLeft)
        row += 1
        self.radioBar = QProgressBar(self)
        self.radioBar.setValue(0)
        l.addWidget(QLabel('Radio'), row, 0, 1, 1, Qt.AlignLeft)
        l.addWidget(self.radioBar, row, 1, 1, 2, Qt.AlignLeft)
        row += 1

        self.editParameterButton = QPushButton('Edit Parameters')
        self.editParameterButton.setEnabled(False)
        l.addWidget(self.editParameterButton, row, 0, 1, 1, Qt.AlignLeft)

        self.connectButton = QPushButton('Connect')
        self.connectLabelShown = True
        self.connectButton.clicked.connect(self.toggleButtonLabel)
        l.addWidget(self.connectButton, row, 1, 1, 1, Qt.AlignLeft)

        self.localGPSButton = QPushButton('Local GPS')
        self.gpsLabelShown = True
        self.localGPSButton.clicked.connect(self.toggleGPSButtonLabel)
        l.addWidget(self.localGPSButton, row, 2, 1, 1, Qt.AlignLeft)

        self.setLayout(l)

    def updateBatteryStatus(self, voltage, current, remaining):
        self.battVoltLabel.setText('{}V'.format(voltage))
        self.battBar.setValue(remaining)
        if remaining >= 60:
            self.battBar.setStyleSheet(BATTERY_BAR_STYLE_TEMPLATE.format('green'))
        elif remaining >= 30:
            self.battBar.setStyleSheet(BATTERY_BAR_STYLE_TEMPLATE.format('yellow'))
        else:
            self.battBar.setStyleSheet(BATTERY_BAR_STYLE_TEMPLATE.format('red'))

    def updateGPSFixStatus(self, fix):
        if fix in GPS_FIX_LABELS:
            self.gpsLbl.setText(GPS_FIX_LABELS[fix])
        else:
            self.gpsLbl.setText(GPS_FIX_LABELS[mavlink.GPS_FIX_TYPE_NO_FIX])

    def toggleButtonLabel(self, isConnected = False):
        if self.connectLabelShown:
            self.connectToMAVLink.emit()
            # TODO add a timer to re-enable connect button after timeout
            self.connectButton.setEnabled(False)
            if isConnected:
                self.connectLabelShown = False
                self.connectButton.setText('Disconnect')
                self.connectButton.setEnabled(True)
        else:
            self.disconnectFromMAVLink.emit()
            self.connectLabelShown = True
            self.editParameterButton.setEnabled(False)
            self.connectButton.setText('Connect')

    def toggleGPSButtonLabel(self, isConnected = False):
        if self.gpsLabelShown:
            self.connectToLocalGPS.emit()
            if isConnected:
                self.gpsLabelShown = False
                self.localGPSButton.setText('Disconnect GPS')
        else:
            self.disconnectFromLocalGPS.emit()
            self.gpsLabelShown = True
            self.localGPSButton.setText('Local GPS')

# test
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ssp = SystemStatusPanel()
    ssp.show()
    sys.exit(app.exec_())
