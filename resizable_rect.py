from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

from text_detection_target import TextDetectionTargetWithResult


class ResizableRect(QGraphicsRectItem):
    selected_edge = None

    def __init__(self, x, y, width, height, onCenter=False):
        if onCenter:
            super().__init__(-width / 2, -height / 2, width, height)
        else:
            super().__init__(0, 0, width, height)
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self.setPen(QPen(QBrush(Qt.GlobalColor.red), 3))

    def getOriginalRect(self):
        # get the original rect adjusted by the pen width
        rect = self.rect()
        border = 0  # self.pen().width() / 2
        return QRectF(
            rect.x() + border,
            rect.y() + border,
            rect.width() - border * 2,
            rect.height() - border * 2,
        )

    def getEdges(self, pos):
        rect = self.rect()
        border = self.pen().width() + 2

        edge = None
        if pos.x() < rect.x() + border:
            edge = edge | Qt.Edge.LeftEdge if edge else Qt.Edge.LeftEdge
        elif pos.x() > rect.right() - border:
            edge = edge | Qt.Edge.RightEdge if edge else Qt.Edge.RightEdge
        if pos.y() < rect.y() + border:
            edge = edge | Qt.Edge.TopEdge if edge else Qt.Edge.TopEdge
        elif pos.y() > rect.bottom() - border:
            edge = edge | Qt.Edge.BottomEdge if edge else Qt.Edge.BottomEdge

        return edge

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected_edge = self.getEdges(event.pos())
            self.offset = QPointF()
        else:
            self.selected_edge = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.selected_edge:
            mouse_delta = event.pos() - event.buttonDownPos(Qt.MouseButton.LeftButton)
            rect = self.rect()
            pos_delta = QPointF()
            border = self.pen().width()

            if self.selected_edge & Qt.Edge.LeftEdge:
                # ensure that the width is *always* positive, otherwise limit
                # both the delta position and width, based on the border size
                diff = min(mouse_delta.x() - self.offset.x(), rect.width() - border)
                if rect.x() < 0:
                    offset = diff / 2
                    self.offset.setX(self.offset.x() + offset)
                    pos_delta.setX(offset)
                    rect.adjust(offset, 0, -offset, 0)
                else:
                    pos_delta.setX(diff)
                    rect.setWidth(rect.width() - diff)
            elif self.selected_edge & Qt.Edge.RightEdge:
                if rect.x() < 0:
                    diff = max(mouse_delta.x() - self.offset.x(), border - rect.width())
                    offset = diff / 2
                    self.offset.setX(self.offset.x() + offset)
                    pos_delta.setX(offset)
                    rect.adjust(-offset, 0, offset, 0)
                else:
                    rect.setWidth(max(border, event.pos().x() - rect.x()))

            if self.selected_edge & Qt.Edge.TopEdge:
                # similarly to what done for LeftEdge, but for the height
                diff = min(mouse_delta.y() - self.offset.y(), rect.height() - border)
                if rect.y() < 0:
                    offset = diff / 2
                    self.offset.setY(self.offset.y() + offset)
                    pos_delta.setY(offset)
                    rect.adjust(0, offset, 0, -offset)
                else:
                    pos_delta.setY(diff)
                    rect.setHeight(rect.height() - diff)
            elif self.selected_edge & Qt.Edge.BottomEdge:
                if rect.y() < 0:
                    diff = max(
                        mouse_delta.y() - self.offset.y(), border - rect.height()
                    )
                    offset = diff / 2
                    self.offset.setY(self.offset.y() + offset)
                    pos_delta.setY(offset)
                    rect.adjust(0, -offset, 0, offset)
                else:
                    rect.setHeight(max(border, event.pos().y() - rect.y()))

            if rect != self.rect():
                self.setRect(rect)
                if pos_delta:
                    self.setPos(self.pos() + pos_delta)
        else:
            # use the default implementation for ItemIsMovable
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.selected_edge = None
        super().mouseReleaseEvent(event)

    def hoverMoveEvent(self, event):
        edges = self.getEdges(event.pos())
        if not edges:
            # self.unsetCursor()
            # show a moving cursor when the mouse is over the item
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif edges in (
            Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
            Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
        ):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges in (
            Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
            Qt.Edge.TopEdge | Qt.Edge.RightEdge,
        ):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        super().hoverMoveEvent(event)


class ResizableRectWithNameTypeAndResult(ResizableRect):
    def __init__(
        self,
        x,
        y,
        width,
        height,
        name,
        image_size,
        result="",
        onCenter=False,
        boxChangedCallback=None,
        itemSelectedCallback=None,
        showOCRRects=True,
    ):
        super().__init__(x, y, width, height, onCenter)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setAcceptHoverEvents(True)
        self.name = name
        self.result = result
        self.boxChangedCallback = boxChangedCallback
        self.itemSelectedCallback = itemSelectedCallback
        self.posItem = QGraphicsSimpleTextItem("{}".format(self.name), parent=self)
        self.posItem.setBrush(QBrush(QColor("red")))
        fontPos = QFont("Arial", int(image_size / 60) if image_size > 0 else 32)
        fontPos.setWeight(QFont.Weight.Bold)
        self.posItem.setFont(fontPos)
        self.resultItem = QGraphicsSimpleTextItem("{}".format(self.result), parent=self)
        self.resultItem.setBrush(QBrush(QColor("red")))
        fontRes = QFont("Arial", int(image_size / 75) if image_size > 0 else 20)
        fontRes.setWeight(QFont.Weight.Bold)
        self.resultItem.setFont(fontRes)
        # add a semitraansparent background to the text using another rect
        self.bgItem = QGraphicsRectItem(self.posItem.boundingRect(), parent=self)
        self.bgItem.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.bgItem.setPen(QPen(Qt.GlobalColor.transparent))
        xpos = (
            self.boundingRect().x()
            - self.posItem.boundingRect().width() / 2
            + self.boundingRect().width() / 2
        )
        ypos = self.boundingRect().y() - self.posItem.boundingRect().height()
        # set the text position to the top left corner of the rect
        self.posItem.setPos(xpos, ypos)
        self.bgItem.setPos(xpos, ypos)
        # z order the text over the rect
        self.posItem.setZValue(2)
        self.bgItem.setZValue(1)
        self.effectiveRect = None
        self.extraBoxes = []
        self.showOCRRects = showOCRRects

    def getRect(self):
        return self.getOriginalRect()

    def updateResult(self, targetWithResult: TextDetectionTargetWithResult):
        self.result = targetWithResult.result
        self.resultItem.setText(targetWithResult.result)
        # set the result color based on the state
        if (
            targetWithResult.result_state
            == TextDetectionTargetWithResult.ResultState.Success
        ):
            self.resultItem.setBrush(QBrush(QColor("green")))
        elif (
            targetWithResult.result_state
            == TextDetectionTargetWithResult.ResultState.SameNoChange
        ):
            self.resultItem.setBrush(QBrush(QColor("lightgreen")))
        elif (
            targetWithResult.result_state
            == TextDetectionTargetWithResult.ResultState.FailedFilter
        ):
            self.resultItem.setBrush(QBrush(QColor("yellow")))
        elif (
            targetWithResult.result_state
            == TextDetectionTargetWithResult.ResultState.Empty
        ):
            self.resultItem.setText("EMP")
            self.resultItem.setBrush(QBrush(QColor("red")))
        else:
            self.resultItem.setBrush(QBrush(QColor("white")))
        # set the result position to the lower left corner of the rect
        self.resultItem.setPos(
            self.boundingRect().x() + self.pen().width(),
            self.boundingRect().y()
            + self.boundingRect().height()
            - self.resultItem.boundingRect().height(),
        )
        self.resultItem.setZValue(2)

        if not self.showOCRRects:
            # do not show the effective rect and extra boxes
            if self.effectiveRect is not None:
                self.effectiveRect.hide()
            for extraBox in self.extraBoxes:
                # remove from the scene
                extraBox.hide()
                self.scene().removeItem(extraBox)
            self.extraBoxes.clear()
            return
        else:
            if self.effectiveRect is not None:
                self.effectiveRect.show()

        if targetWithResult.effectiveRect is not None:
            # draw the effective rect in the scene
            if self.effectiveRect is None:
                self.effectiveRect = QGraphicsRectItem(
                    targetWithResult.effectiveRect, parent=self
                )
                # ignore any mouse events on the effective rect
                self.effectiveRect.setAcceptHoverEvents(False)
                self.effectiveRect.setAcceptDrops(False)
                self.effectiveRect.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self.effectiveRect.setBrush(QBrush(QColor(0, 0, 0, 0)))
                self.effectiveRect.setPen(QPen(QColor("green"), 3))
                self.effectiveRect.setZValue(-1)
            else:
                self.effectiveRect.setRect(targetWithResult.effectiveRect)
        else:
            if self.effectiveRect is not None:
                self.effectiveRect.hide()
        if (
            targetWithResult.extras is not None
            and "boxes" in targetWithResult.extras
            and len(targetWithResult.extras["boxes"]) > 0
        ):
            if len(self.extraBoxes) > 0:
                for extraBox in self.extraBoxes:
                    # remove from the scene
                    extraBox.hide()
                    self.scene().removeItem(extraBox)
                self.extraBoxes.clear()
            for box in targetWithResult.extras["boxes"]:
                if not ("x" in box and "y" in box and "w" in box and "h" in box):
                    continue
                # draw the extra boxes in the scene
                extraRect = QGraphicsRectItem(
                    QRectF(box["x"], box["y"], box["w"], box["h"]), parent=self
                )
                # ignore any mouse events on the extra rect
                extraRect.setAcceptHoverEvents(False)
                extraRect.setAcceptDrops(False)
                extraRect.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                extraRect.setBrush(QBrush(QColor(0, 0, 0, 0)))
                extraRect.setPen(QPen(QColor("blue"), 3))
                extraRect.setZValue(-2)
                self.extraBoxes.append(extraRect)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        origRect = self.getRect()
        boxRect = QRectF(
            origRect.x() + self.x(),
            origRect.y() + self.y(),
            origRect.width(),
            origRect.height(),
        )
        self.boxChangedCallback(self.name, boxRect)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.itemSelectedCallback(self.name)

    def mouseMoveEvent(self, event):
        return super().mouseMoveEvent(event)