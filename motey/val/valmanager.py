import os

from rx.subjects import Subject
from yapsy.PluginManager import PluginManager

from motey.repositories.labeling_repository import LabelingRepository
from motey.decorators.singleton import Singleton
from motey.utils.logger import Logger


@Singleton
class VALManager(object):
    """
    Manger for all the virtual abstraction layer plugins.
    Loads the plugins and wrapps the commands.
    This class is implemented as a Singleton and should be called via VALManager.Instance().
    """

    def __init__(self):
        """
        Constructor of the VALManger.
        """

        self.plugin_stream = Subject()
        self.logger = Logger.Instance()
        self.labeling_engine = LabelingRepository.Instance()
        self.plugin_manager = PluginManager()
        self.register_plugins()

    def register_plugins(self):
        """
        Register all the available plugins.
        A plugin has to be located under motey/val/plugins.
        After all the available plugins are loaded, the ``activate`` method of the plugin will be executed and a label
        with the related plugin type will be added to the labeling engine.
        """

        self.labeling_engine.remove_all_from_type('plugin')
        self.plugin_manager.setPluginPlaces([os.path.abspath("motey/val/plugins")])
        self.plugin_manager.collectPlugins()
        for plugin in self.plugin_manager.getAllPlugins():
            plugin.plugin_object.activate()
            self.labeling_engine.add(plugin.plugin_object.get_plugin_type(), 'plugin')

    def instantiate(self, image_name, plugin_type=None):
        """
        Instantiate an image.

        :param image_name: The image_name can be type of str or list. The list can contain again str or a dict.
         If the image_name is a str, the instance with this specific name will be instantiated, if it a list with str in
         it, all the images in the list will be instanciated and if it is a list with a dict in it, each dict needs to
         have a key ``image_name```in it and an optional key ``parameters```which can be again a dict with different
         execution parameters.

         samples:
          image_name = 'alpine'
          image_name = ['alpine', 'busybox',]
          image_name = [{'image_name': 'alpine', 'parameters': {'ports': {'80/tcp': 8080}, 'name': 'motey_alpine'}},]
        :param plugin_type: Will only be executed with the given plugin. Could be a str or a list. Default None.
        """

        for plugin in self.plugin_manager.getAllPlugins():
            print(image_name)
            if isinstance(image_name, str):
                plugin.plugin_object.start_instance(image_name)
            elif isinstance(image_name, list):
                for single_image in image_name:
                    if isinstance(single_image, str):
                        plugin.plugin_object.start_instance(single_image)
                    elif isinstance(single_image, dict):
                        parameters = single_image['parameters'] if 'parameters' in single_image else {}
                        plugin.plugin_object.start_instance(single_image['image_name'], parameters)

    def close(self):
        """
        Will clean up the VALManager.
        At first it will remove the label from the labeling engine and afterwards all the ``deactivate`` method for
        each plugin will be executed.
        """

        for plugin in self.plugin_manager.getAllPlugins():
            self.labeling_engine.remove(plugin.plugin_object.get_plugin_type())
            plugin.plugin_object.deactivate()
