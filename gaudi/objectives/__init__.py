#!/usr/bin/python

##############
# GAUDIasm: Genetic Algorithms for Universal
# Design Inference and Atomic Scale Modeling
# Authors:  Jaime Rodriguez-Guerra Pedregal
#            <jaime.rodriguezguerra@uab.cat>
#           Jean-Didier Marechal
#            <jeandidier.marechal@uab.cat>
# Web: https://bitbucket.org/jrgp/gaudi
##############

# Python
import abc
import logging
# GAUDI
from gaudi import plugin

logger = logging.getLogger(__name__)


class ObjectiveProvider(object):

    """
    Base class that every `objectives` plugin MUST inherit.

    Mount point for plugins implementing new objectives to be evaluated by DEAP.
    The objective resides within the Fitness attribute of the individual.
    Do whatever you want, but use an evaluate() function to return the results.
    Apart from that, there's no requirements.

    The base class includes some useful attributes, so don't forget to call
    `ObjectiveProvider.__init__` in your overriden `__init__`. For example,
    `self.parent` is a reference to the individual to be evaluated, while+
    `self.env` is a `Chimera.selection.ItemizedSelection` object which is shared among
    all objectives. Use that to get atoms in the surrounding of the target gene, and
    remember to `self.env.clear()` it before use.

    ---
    From (M.A. itself)[http://martyalchin.com/2008/jan/10/simple-plugin-framework/]:
    Now that we have a mount point, we can start stacking plugins onto it.
    As mentioned above, individual plugins will subclass the mount point.
    Because that also means inheriting the metaclass, the act of subclassing
    alone will suffice as plugin registration. Of course, the goal is to have
    plugins actually do something, so there would be more to it than just
    defining a base class, but the point is that the entire contents of the
    class declaration can be specific to the plugin being written. The plugin
    framework itself has absolutely no expectation for how you build the class,
    allowing maximum flexibility. Duck typing at its finest.
    """

    __metaclass__ = plugin.PluginMount

    def __init__(self, parent=None, name=None, weight=None, cache=None, environment=None,
                 **kwargs):
        self.parent = parent
        self.name = name
        self.weight = weight
        self.env = environment
        try:
            self._cache = cache[self.name]
        except KeyError:
            self._cache = cache[self.name] = {}

    @abc.abstractmethod
    def evaluate(self):
        """
        Return the score of the individual under the current conditions.
        """