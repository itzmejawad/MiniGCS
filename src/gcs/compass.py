from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout, QGraphicsItem, QGraphicsScene, QGraphicsView
from PyQt5.QtSvg import QGraphicsSvgItem, QSvgRenderer
from PyQt5.QtCore import Qt

class Compass(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel('Heading: 0.0' + u"\u00b0")
        svgRenderer = QSvgRenderer('res/compass.svg')
        self.compass = QGraphicsSvgItem()
        self.compass.setSharedRenderer(svgRenderer)
        self.compass.setCacheMode(QGraphicsItem.NoCache)
        self.compass.setElementId('needle')

        center = self.compass.boundingRect().center()
        self.compass.setTransformOriginPoint(center.x(), center.y())

        bkgnd = QGraphicsSvgItem()
        bkgnd.setSharedRenderer(svgRenderer)
        bkgnd.setCacheMode(QGraphicsItem.NoCache)
        bkgnd.setElementId('background')

        self.compass.setPos(bkgnd.boundingRect().width() / 2 - self.compass.boundingRect().width() / 2,
                            bkgnd.boundingRect().height() / 2 - self.compass.boundingRect().height() / 2)

        self.compass.setTransformOriginPoint(self.compass.boundingRect().width() / 2, self.compass.boundingRect().height() / 2)

        fregnd = QGraphicsSvgItem()
        fregnd.setSharedRenderer(svgRenderer)
        fregnd.setCacheMode(QGraphicsItem.NoCache)
        fregnd.setElementId('foreground')

        scene = QGraphicsScene()
        scene.addItem(bkgnd)
        scene.addItem(self.compass)
        scene.addItem(fregnd)
        scene.setSceneRect(bkgnd.boundingRect())

        view = QGraphicsView(scene)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(view)
        super().setLayout(layout)

    def setHeading(self, hdr):
        self.compass.setRotation(360.0 - hdr)
        self.label.setText('Heading: ' + str(hdr) + u"\u00b0")