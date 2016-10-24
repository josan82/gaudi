#!/usr/bin/env python
# -*- coding: utf-8 -*-

##############
# GAUDIasm: Genetic Algorithms for Universal
# Design Inference and Atomic Scale Modeling
# Authors:  Jaime Rodriguez-Guerra Pedregal
#            <jaime.rodriguezguerra@uab.cat>
#           Jean-Didier Marechal
#            <jeandidier.marechal@uab.cat>
# Web: https://bitbucket.org/insilichem/gaudi
##############

"""
This module implements evolutionary algorithms as seen in DEAP,
and extends their functionality to make use of GAUDI goodies.

In its current state, it's just a copy of deap's ea_mu_plus_lambda.

.. todo::

    * Job progress

    * Custom debug info

    * Genealogy

"""

from __future__ import print_function, division
import sys
import os
import logging
from time import time, strftime
from datetime import timedelta
from deap import tools
from deap.algorithms import varOr
import yaml
import gaudi

logger = logging.getLogger(__name__)

if sys.version_info.major == 3:
    xrange = range
    raw_input = input

def ea_mu_plus_lambda(population, toolbox, mu, lambda_, cxpb, mutpb, ngen, cfg,
                      stats=None, halloffame=None, verbose=True):
    """This is the :math:`(\mu + \lambda)` evolutionary algorithm.

    :param population: A list of individuals.
    :param toolbox: A :class:`~deap.base.Toolbox` that contains the evolution
                    operators.
    :param mu: The number of individuals to select for the next generation.
    :param lambda\_: The number of children to produce at each generation.
    :param cxpb: The probability that an offspring is produced by crossover.
    :param mutpb: The probability that an offspring is produced by mutation.
    :param ngen: The number of generation.
    :param stats: A :class:`~deap.tools.Statistics` object that is updated
                  inplace, optional.
    :param halloffame: A :class:`~deap.tools.HallOfFame` object that will
                       contain the best individuals, optional.
    :param verbose: Whether or not to log the statistics.
    :returns: The final population.

    First, the individuals having an invalid fitness are evaluated. Then, the
    evolutionary loop begins by producing *lambda_* offspring from the
    population, the offspring are generated by a crossover, a mutation or a
    reproduction proportionally to the probabilities *cxpb*, *mutpb* and 1 -
    (cxpb + mutpb). The offspring are then evaluated and the next generation
    population is selected from both the offspring **and** the population.
    Briefly, the operators are applied as following ::

        evaluate(population)
        for i in range(ngen):
            offspring = varOr(population, toolbox, lambda_, cxpb, mutpb)
            evaluate(offspring)
            population = select(population + offspring, mu)

    This function expects :meth:`toolbox.mate`, :meth:`toolbox.mutate`,
    :meth:`toolbox.select` and :meth:`toolbox.evaluate` aliases to be
    registered in the toolbox. This algorithm uses the :func:`varOr`
    variation.
    """
    t0 = time()
    population_ = population[:]
    logbook = tools.Logbook()
    logbook.header = ['gen', 'progress', 'nevals', 'speed', 'eta'] + (stats.fields if stats else [])

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    if halloffame is not None:
        halloffame.update(population)

    record = stats.compile(population) if stats is not None else {}
    nevals = len(invalid_ind)
    t1 = time()
    speed = nevals / (t1-t0)
    performed_evals = nevals
    estimated_evals = (ngen + 1) * lambda_ * (cxpb + mutpb)
    remaining_evals = estimated_evals - performed_evals
    remaining = timedelta(seconds=int(remaining_evals / speed))
    progress = '{:.2f}%'.format(100/(ngen+1))
    logbook.record(gen=0, progress=progress, nevals=nevals, 
                   speed='{:.2f} ev/s'.format(speed), eta=remaining, **record)
    if verbose:
        logger.log(100, logbook.stream)

    # Begin the generational process
    for gen in xrange(1, ngen + 1):
        try:
            # Vary the population
            t0 = time()
            offspring = varOr(population, toolbox, lambda_, cxpb, mutpb)

            # Evaluate the individuals with an invalid fitness
            t1 = time()
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            # Update the hall of fame with the generated individuals # every 2 generations
            if halloffame is not None: # and not gen % 2:
                halloffame.update(offspring)

            # Select the next generation population
            population[:] = toolbox.select(population + offspring, mu)

            # Update the statistics with the new population
            nevals = len(invalid_ind)
            t2 = time()
            ev_speed = nevals / (t2-t1)
            speed = nevals / (t2-t0)
            performed_evals += nevals
            remaining_evals = estimated_evals - performed_evals
            remaining = timedelta(seconds=int(remaining_evals / speed))
            record = stats.compile(population) if stats is not None else {}
            progress = '{:.2f}%'.format(100*(gen+1)/(ngen+1))
            logbook.record(gen=gen, progress=progress, nevals=nevals,
                           speed='{:.2f} ev/s'.format(ev_speed), eta=remaining, **record)
            if verbose:
                logger.log(100, logbook.stream)
        except (Exception, KeyboardInterrupt) as e:
            logger.error(e)
            answer = raw_input('\nInterruption detected. Write results so far? (y/N): ')
            if answer.lower() not in ('y', 'yes'):
                sys.exit('Ok, bye!')
            for individual in population:
                try:
                    individual.unexpress()
                except Exception:  # individual was already unexpressed
                    pass
            break
        else:
            # Save a copy of an fully evaluated population, in case the 
            # simulation is stopped in next generation.
            population_ = population[:]
            if halloffame and cfg.output.check_every and not gen % cfg.output.check_every:
                try:
                    dump_population(halloffame, cfg, subdir='check{}'.format(gen))
                except Exception:
                    logger.warn('Could not write checkpoing for gen #%s', gen)
    return population_, logbook

def dump_population(population, cfg, subdir=None):
    logger.log(100, 'Writing %s results to disk', len(population))
    results = {'GAUDI.objectives': ['{} ({})'.format(obj.name, obj.module) for obj in cfg.objectives]}
    results['GAUDI.results'] = {}
    basepath = cfg.output.path
    if subdir is not None:
        try:
            basepath = os.path.join(cfg.output.path, subdir)
            os.mkdir(basepath)
        except (IOError, OSError):
            pass
    for i, ind in enumerate(population):
        filename = ind.write(i, path=basepath)
        results['GAUDI.results'][os.path.basename(filename)] = map(float, ind.fitness.values)
    gaudi_output = os.path.join(basepath, cfg.output.name + '.gaudi-output')
    with open(gaudi_output, 'w+') as out:
        out.write('# Generated by GAUDI v{} on {}\n\n'.format(gaudi.__version__,
                                                              strftime("%Y-%m-%d %H:%M:%S")))
        out.write(yaml.safe_dump(results, default_flow_style=False))