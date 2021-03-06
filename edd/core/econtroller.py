import uuid
import json

from edd.core.eobject import EObject
from edd.core.eattribute import EAttribute
from edd.core.enodehandle import ENodeHandle
from edd.core.egraphhandle import EGraphHandle


class EController(EObject):

    kMessageNodeAdded = EObject()
    kMessageNodeRemoved = EObject()

    kMessageNodeUpdate = EObject()

    kMessageEditBegin = EObject()
    kMessageEditEnd = EObject()

    kMessageUnknown = EObject()
    kMessageInternalError = EObject()

    kMessageConnectionMade = EObject()
    kMessageConnectionBroke = EObject()

    def __init__(self):
        EObject.__init__(self)

        self.__scene = None
        self.__regNodes = {}
        self.__graphHandle = EGraphHandle()

    @property
    def Handle(self):
        return self.__graphHandle

    @property
    def NodeTypes(self):
        return self.__regNodes.keys()

    def setScene(self, scene):
        self.__scene = scene

    def getScene(self):
        return self.__scene

    def registerNode(self, nodeName, nodeHandle):
        self.__regNodes[nodeName] = nodeHandle

    def getNode(self, theNode):
        if isinstance(theNode, uuid.UUID):
            return self.__scene.getNodes()[theNode].Handle

        elif isinstance(theNode, basestring):
            for nodeId, node in self.__scene.getNodes().iteritems():
                if theNode == node.Name:
                    return node.Handle

        return None

    def getTransform(self, theNode):

        node = None

        if isinstance(theNode, ENodeHandle):
            return self.__scene.getNodes()[self.getNode(theNode.Id).Id]

        if isinstance(theNode, basestring):
            return self.__scene.getNodes()[self.getNode(theNode).Id]

        return node

    def createNode(self, nodeType, nodeName=None):

        if self.__regNodes.has_key(nodeType):
            nodeHandle = self.__graphHandle.addHandle(self.__regNodes[nodeType]())

            self.Message.emit(self.kMessageNodeAdded.setData([nodeHandle, nodeName]))

            return nodeHandle

        return None

    def deleteNode(self, node):

        if isinstance(node, basestring):
            node = self.getNode(node)
            theId = self.__graphHandle.delHandle(node.Id)

        elif isinstance(node, uuid.UUID):
            theId = self.__graphHandle.delHandle(node)

        self.Message.emit(self.kMessageNodeRemoved.setData(theId))

    def connectAttr(self, attrOne, attrTwo):

        data = []

        if isinstance(attrOne, EAttribute) and isinstance(attrTwo, EAttribute):
            data = self.__graphHandle.connectAttributes(attrOne, attrTwo)

        elif isinstance(attrOne, basestring) and isinstance(attrTwo, basestring):

            nodeOneName, attrOneName = attrOne.split('.')
            nodeTwoName, attrTwoName = attrTwo.split('.')

            attrOne = self.getNode(nodeOneName).getAttributeByName(attrOneName)
            attrTwo = self.getNode(nodeTwoName).getAttributeByName(attrTwoName)

            if attrOne and attrTwo:
                data = self.__graphHandle.connectAttributes(attrOne, attrTwo)

        elif isinstance(attrOne, uuid.UUID) and isinstance(attrTwo, uuid.UUID):
            attrOne = self.__graphHandle.getAttributeFromId(attrOne)
            attrTwo = self.__graphHandle.getAttributeFromId(attrTwo)

            data = self.__graphHandle.connectAttributes(attrOne, attrTwo)

        self.Message.emit(self.kMessageConnectionMade.setData(data))

        return data

    def ls(self):
        return [node.Name for node in self.__scene.getNodes().itervalues()]

    def reset(self):
        self.__graphHandle.reset()

    def __getNodeCreateCmd(self, nodeTransform):

        return dict({'TYPE': nodeTransform.Handle.NodeType,
                     'PX': nodeTransform.scenePos().x(),
                     'PY': nodeTransform.scenePos().y()})

    def __getNodePropertySetCmd(self, nodeTransform):
        return

    def __getConnectionCreateCmd(self, connection):
        headNode = self.getNode(self.__graphHandle.getAttributeHandleId(connection.Head.Id))
        tailNode = self.getNode(self.__graphHandle.getAttributeHandleId(connection.Tail.Id))
        return dict({'HEAD': '%s.%s' % (self.getTransform(headNode).Name, connection.Head.Name),
                     'TAIL': '%s.%s' % (self.getTransform(tailNode).Name, connection.Tail.Name)})

    def save(self, sceneFile):
        saveData = dict({'NODES': {}, 'CONNECTIONS': []})

        for nodeName in self.ls():
            saveData['NODES'][nodeName] = self.__getNodeCreateCmd(self.getTransform(nodeName))

        for conn in self.__scene.getConnections():
            tConn = self.__graphHandle.getConnection(conn)
            saveData['CONNECTIONS'].append(self.__getConnectionCreateCmd(tConn))

        sceneFile = open(sceneFile, 'w')
        sceneFile.write(json.dumps(saveData, indent=4, separators=(',', ': ')))
        sceneFile.close()

    def load(self, sceneFile):
        loadData = json.loads(open(sceneFile).read())

        for nodeName, nodeData in loadData['NODES'].iteritems():
            self.getTransform(self.createNode(nodeData['TYPE'], nodeName)).setPos(nodeData['PX'], nodeData['PY'])

        for connData in loadData['CONNECTIONS']:
            self.connectAttr(connData['HEAD'], connData['TAIL'])