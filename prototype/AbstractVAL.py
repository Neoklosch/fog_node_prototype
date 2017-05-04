class AbstractVAL(object):
    def hasImage(self, image_name):
        raise NotImplementedError("Should have implemented this")

    def loadImage(self, image_name):
        raise NotImplementedError("Should have implemented this")

    def deleteImage(self, image_name):
        raise NotImplementedError("Should have implemented this")

    def createInstance(self, image_name):
        raise NotImplementedError("Should have implemented this")

    def startInstance(self, container_name):
        raise NotImplementedError("Should have implemented this")

    def stopInstance(self, container_name):
        raise NotImplementedError("Should have implemented this")

    def getStats(self, container_name):
        raise NotImplementedError("Should have implemented this")
