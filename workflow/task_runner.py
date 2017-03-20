# coding: utf-8
import inspect
import logging
import importlib
from django.conf import settings
from celery import group, chain
from celery import current_app
from .choices import INNER_STATE_RUNNING
from .models import AvailableTask
from .tasks import BaseTask, ChangeStateTask


logger = logging.getLogger(__name__)


def is_subclass(o):
    return inspect.isclass(o) and issubclass(o, BaseTask)


class AvailableTaskLoader(object):

    def _get_subclasses(self):
        task_dict = {}
        for app in settings.INSTALLED_APPS:
            try:
                mod = __import__('%s.%s' % (app, 'tasks'))
            except:
                continue
            members = inspect.getmembers(mod.tasks, predicate=lambda x: inspect.isclass(x) and issubclass(x, BaseTask))
            for m in members:
                # {'foo.bar.Task': 'class <foo.bar.Task>'}
                task_dict['{0}.{1}'.format(m[1].__module__, m[0])] = m[1]
        return task_dict

    def load(self):
        subcls = self._get_subclasses()
        for cls_name, cls in subcls.items():

            current_app.tasks.register(cls)

            if not hasattr(cls, 'public') or not cls.public:
                continue
            full_name = '{0}.{1}'.format(cls.__module__, cls.__name__)
            name = cls.name if cls.name else cls.__name__
            description = cls.description if cls.description else cls.__doc__
            try:
                obj, created = AvailableTask.objects.get_or_create(name=name,
                                                                   klass=full_name,
                                                                   description=description)
                logger.info('AvailableTask %s created successfully.', full_name)
            except Exception as ex:
                logger.warning('Error while creating %s. %s',
                               full_name,
                               ex.message)

        self._prune()

    def _prune(self):
        '''removes all the unecessary tasks'''
        tasks = set([member for member in self._get_subclasses().keys()])
        existing = set(AvailableTask.objects.all().values_list('klass', flat=True))
        stale = existing - tasks
        for s in stale:
            at = AvailableTask.objects.get(klass=s)
            at.transition_tasks.all().delete()
            at.delete()


class TaskLoader(object):

    def load_task(self, task):

        parts = task.split('.')

        try:
            module_name = '.'.join(parts[:-1])
            klass_name = parts[-1]
            module = importlib.import_module(module_name)
            klass = getattr(module, klass_name)
            return klass
        except:
            raise ValueError('Cannot load task {0}'.format(task))


class TaskRunner(object):

    def __init__(self, controller, next, task_loader=None):

        '''initializes a task'''

        if not controller:
            raise ValueError('Controller cannot be null.')

        if not next:
            raise ValueError('Next state cannot be null')

        self.task_loader = task_loader if task_loader is not None else TaskLoader()

        # supports passing controlled or controller objects
        if hasattr(controller, 'controller'):
            self.controller = controller.controller
            self.controlled = controller
        else:
            self.controller = controller
            self.controlled = controller.content_object

        self.next = next
        self.transition = self.get_transition()
        self.initialize_tasks()

    def get_transition(self):
        transitions = self.controller.machine.transitions.filter(from_state=self.controller.current_state,
                                                                 to_state=self.next)
        if transitions.count() != 1:
            raise ValueError('invalid transition for this taskrunner')

        return transitions.first()

    def initialize_tasks(self):

        '''loads and initializes all the tasks'''
        self.tasks = [self.task_loader.load_task(t.klass)()
                      for t in self.transition.tasks.all()]
        self.tasks.append(ChangeStateTask())

        self.validation_tasks = [self.task_loader.load_task(t.validation_class)()
                                 for t in self.tasks if t.validation_class and
                                 t.validation_class != '']

    def run(self):

        '''executes the tasks'''
        cid = self.controller.id
        nsi = self.next.id

        validation = group([v.s(cid=cid, nsi=nsi)
                            for v in self.validation_tasks])

        tasks = chain([t.s(cid=cid, nsi=nsi)
                       for t in self.tasks])
        if len(validation.tasks) > 0:
            job = chain(validation, tasks)
        else:
            job = tasks

        self.controller.inner_state = INNER_STATE_RUNNING
        self.controller.save()
        return job.delay()
