import threading
import paho.mqtt.client as mqtt
from motey.utils.logger import Logger
from motey.database.nodes_database import NodesDatabase


class MQTTServer(object):
    ROUTES = {
        'blueprint': 'motey/blueprint',
        'capabilities': 'motey/capabilities',
        'node_status': 'motey/node_status',
        'register_node': 'motey/register',
        'remove_node': 'motey/remove',
        'receive_nodes': 'motey/receive_nodes'
    }

    def __init__(self, host, port, username, password, keepalive=60):
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.username = username
        self.password = password
        self.logger = Logger.Instance()
        self.database = NodesDatabase.Instance()
        self.client = mqtt.Client()
        self.client.username_pw_set(username=self.username, password=self.password)
        self.client.on_connect = self.handle_on_connect
        self.client.on_subscribe = self.handle_on_subscribe
        self.register_routes()
        self.client.on_unsubscribe = self.handle_on_unsubscribe
        self.client.on_disconnect = self.handle_on_disconnect
        self._after_connect = None
        self.run_server_thread = threading.Thread(target=self.run_server, args=())
        self.run_server_thread.daemon = True

    @property
    def after_connect(self):
        return self._after_connect

    @after_connect.setter
    def after_connect(self, handler):
        self._after_connect = handler

    def register_routes(self):
        self.client.message_callback_add(sub=self.ROUTES['blueprint'], callback=self.handle_blueprints)
        self.client.message_callback_add(sub=self.ROUTES['capabilities'], callback=self.handle_capabilities)
        self.client.message_callback_add(sub=self.ROUTES['node_status'], callback=self.handle_node_status)
        self.client.message_callback_add(sub=self.ROUTES['receive_nodes'], callback=self.handle_receive_nodes)

    def start(self):
        self.run_server_thread.start()

    def run_server(self):
        try:
            self.client.connect(host=self.host, port=self.port, keepalive=self.keepalive)
            self.client.loop_forever()
        except OSError:
            self.logger.error('MQTT server not available')

    def stop(self):
        self.client.loop_stop()

    def publish_new_node(self, ip):
        if ip:
            self.client.publish(topic=self.ROUTES['register_node'], payload=ip)

    def remove_node(self, ip):
        self.client.publish(topic=self.ROUTES['remove_node'], payload=ip)

    def handle_on_connect(self, client, userdata, flags, resultcode):
        """
        The value of rc indicates success or not:on_connected
            0: Connection successful
            1: Connection refused - incorrect protocol version
            2: Connection refused - invalid client identifier
            3: Connection refused - server unavailable
            4: Connection refused - bad username or password
            5: Connection refused - not authorised
            6-255: Currently unused.
        """

        if resultcode is not 0:
            self.logger.info("Can not connect")
        else:
            self.logger.info("Connected: " + str(resultcode))
            client.subscribe(topic=self.ROUTES['blueprint'])
            client.subscribe(topic=self.ROUTES['capabilities'])
            client.subscribe(topic=self.ROUTES['node_status'])
            client.subscribe(topic=self.ROUTES['receive_nodes'])
        if self._after_connect:
            self._after_connect()

    def handle_on_subscribe(self, client, userdata, mid, granted_qos):
        self.logger.info("Subscribed: " + str(mid) + " " + str(granted_qos))

    def handle_blueprints(self, client, userdata, message):
        print('%s %s' % (message.topic, str(message.payload)))

    def handle_capabilities(self, client, userdata, message):
        print('%s %s' % (message.topic, str(message.payload)))

    def handle_node_status(self, client, userdata, message):
        print('%s %s' % (message.topic, str(message.payload)))

    def handle_receive_nodes(self, client, userdata, message):
        print('handle_receive_nodes')
        new_node = message.payload.decode('utf-8')
        print('payload from receive_nodes callback: %s' % new_node)
        self.database.add(ip=new_node)

    def handle_on_unsubscribe(self, client, userdata, mid):
        self.logger.info("Unsubscribed: " + str(mid))

    def handle_on_disconnect(self, client, userdata, resultcode):
        self.logger.info("Disconnected: " + str(resultcode))