import copy
import threading

import yaml
from jsonschema import validate, ValidationError

from motey.communication.api_routes.blueprintendpoint import BlueprintEndpoint
from motey.models.image import Image
from motey.models.service import Service
from motey.validation.schemas import blueprint_schema


class InterNodeOrchestrator(object):
    """
    This class orchestrates yaml blueprints.
    It will start and stop virtual instances of images defined in the blueprint.
    It also can communicate with other nodes to start instances there if the requirements does not fit with the
    possibilities of the current node.
    """
    def __init__(self, logger, valmanager, service_repository, labeling_repository, node_repository, zeromq_server):
        """
        Instantiates the ``Logger``, the ``VALManagger``, ``ServiceRepository`` and subscribe to the blueprint endpoint.
        """
        self.logger = logger
        self.valmanager = valmanager
        self.service_repository = service_repository
        self.labeling_repository = labeling_repository
        self.node_repository = node_repository
        self.zeromq_server = zeromq_server
        self.blueprint_stream = BlueprintEndpoint.yaml_post_stream.subscribe(self.handle_blueprint)

    def parse_local_blueprint_file(self, file_path):
        """
        Parse a local yaml file and start the virtual images defined in the blueprint.

        :param file_path: Path to the local blueprint file.
        """
        with open(file_path, 'r') as stream:
            self.handle_blueprint(stream)

    def instantiate_service(self, service):
        """
        Instantiate a service.

        :param service: the service to be used.
        """
        if service.action == Service.ServiceAction.ADD:
            self.service_repository.add(service)
            service.state = Service.ServiceState.INSTANTIATING
            self.service_repository.update(service)
            for image in service.images:
                if 'capabilities' not in image:
                    self.deploy_locally([image])
                    continue

                for capability in image.capabilities:
                    if not self.labeling_repository.has(label=capability):
                        external_service = copy.deepcopy(service)
                        external_service.images = []
                        external_service.images.append(copy.deepcopy(image))
                        successfully_deployed = self.deploy_externally(external_service)
                        if not successfully_deployed:
                            service.state = Service.ServiceState.ERROR
                            self.service_repository.update(service)
                        break
                else:  # never broke - all capabilities are succeeded locally
                    self.deploy_locally([image])

            if service.state != Service.ServiceState.ERROR:
                service.state = Service.ServiceState.RUNNING
                self.service_repository.update(service)

    def deploy_locally(self, image):
        # TODO: should return intance id and store them in the image
        self.valmanager.instantiate(image)

    def deploy_externally(self, service):
        for node in self.node_repository.all():
            capabilities = self.zeromq_server.request_capabilities(node)
            if self.compare_capabilities(service.images[0]['capabilities'], capabilities):
                # TODO: deploy externally
                # 1. have an endpoint to deploy to
                # 2. connect to the node
                # 3. send service
                # 4. request status (loop until running or error
                break
        else:  # never broke - no node fulfill capabilities
            return False
        return True

    def compare_capabilities(self, external_capabilities, needed_capabilities):
        """
        Compares to capabilitiy dicts.

        :param external_capabilities: the capabilties to check
        :param needed_capabilities: the capabilities to compare with
        :return: True if all capabilities are fulfilled, otherwiese False
        """
        for external_capability in external_capabilities:
            for capability in needed_capabilities:
                if external_capability['label'] == capability['label'] and \
                   external_capability['type'] == capability['type']:
                    break  # found them
            else:  # never broke - capability not found - break outer loop and try next node
                break
        else:  # never broke - all capabilities succeeded
            return True
        return False

    def terminate_instances(self, service):
        """
        Terminates a service.

        :param service: the service to be used.
        """
        if service.action == Service.ServiceAction.REMOVE:
            if self.service_repository.has(service_id=service.id):
                service.state = Service.ServiceState.STOPPING
                self.service_repository.update(service)
                for image in service.images:
                    self.valmanager.terminate(image.id)
                service.state = Service.ServiceState.TERMINATED
                self.service_repository.update(service)
            else:
                self.logger.error('Service `%s` with the id `%s` is not available' % (service.name, service.id))

    def handle_blueprint(self, blueprint_data):
        """
        Try to load the YAML data from the given blueprint data and validates them by using the
        ``validation.schemas.blueprint_schema``.
        If the data is valid, they will be transformed into a services model and handed over to the ``VALManager``.

        :param blueprint_data: data in YAML format which matches the ``validation.schemas.blueprint_schema``
        """
        try:
            loaded_data = yaml.load(blueprint_data)
            validate(loaded_data, blueprint_schema)
            service = self.__translate_to_service(loaded_data)
            worker_thread = None
            if service.action == Service.ServiceAction.ADD:
                worker_thread = threading.Thread(target=self.instantiate_service, args=(service,))
            elif service.action == Service.ServiceAction.REMOVE:
                worker_thread = threading.Thread(target=self.terminate_instances, args=(service,))
            else:
                self.logger.error(
                    'Action `%s` for service `%s` not a valid action type' % (service.action, service.name))

            if worker_thread:
                worker_thread.daemon = True
                worker_thread.start()

        except (yaml.YAMLError, ValidationError):
            self.logger.error('YAML file could not be parsed: %s' % blueprint_data)

    def __translate_to_service(self, blueprint_data):
        """
        Private method to translate the blueprint data into a service model.

        :param blueprint_data: data in YAML format which matches the ``validation.schemas.blueprint_schema``
        :return: the translated service model
        """
        service = Service()
        service.name = blueprint_data['service_name']
        service.images = self.__translate_to_image_list(blueprint_data['images'])
        return service

    def __translate_to_image_list(self, yaml_data):
        """
        Private method to translate a list of images into a list of image models.

        :param yaml_data: list of images which should be translated
        :return: a list of translated image models
        """
        result_list = []
        for image in yaml_data:
            result_list.append(self.__translate_to_image(image))
        return result_list

    def __translate_to_image(self, yaml_data):
        """
        Private method to translate a single yaml image data into a image model.

        :param yaml_data: a single yaml image data
        :return: the translated image model
        """
        image = Image()
        image.name = yaml_data['image_name']
        image.parameters = yaml_data['parameters']
        image.capabilities = yaml_data['capabilities']
        return image
