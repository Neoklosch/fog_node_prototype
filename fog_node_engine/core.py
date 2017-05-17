from time import sleep

from fog_node_engine.communication.apiserver import APIServer
from fog_node_engine.communication.mqttserver import MQTTServer
from fog_node_engine.database.labeling_database import LabelingDatabase
from fog_node_engine.hardwareevents.hardwareeventengine import HardwareEventEngine
from fog_node_engine.orchestrator.inter_node_orchestrator import LocalOrchestrator
from fog_node_engine.utils.logger import Logger
from fog_node_engine.val.valmanager import VALManager
from fog_node_engine.utils import network_utils


class Core(object):
    def __init__(self):
        self.stopped = False
        self.logger = Logger.Instance()
        self.webserver = APIServer.Instance()
        self.mqttserver = MQTTServer.Instance()
        self.labeling_engine = LabelingDatabase.Instance()
        self.valmanager = VALManager.Instance()
        self.local_orchestrator = LocalOrchestrator.Instance()
        self.mqttserver.after_connect = self.handle_after_connect

    def start(self):
        self.logger.info('App started')
        self.webserver.start()
        self.mqttserver.start()

        hardwareEventEngine = HardwareEventEngine.Instance()

        while not self.stopped:
            for i in range(2):
                print('round: %s' % str(i))
                sleep(2)
                self.valmanager.exec_command()

    def handle_after_connect(self):
        self.mqttserver.publish_new_node(network_utils.get_own_ip())

    def stop(self):
        print('stop the core')
        self.stopped = True
        self.mqttserver.remove_node(network_utils.get_own_ip())
        self.mqttserver.stop()
        self.valmanager.close()
        self.logger.info('App closed')