# coding: utf-8
import logging
from django.apps import AppConfig
from django.conf import settings
from reversion import revisions as reversion


logger = logging.getLogger(__name__)


class WorkflowApp(AppConfig):

    name = 'workflow'
    verbose_name = 'workflow'

    def ready(self):
        from workflow.receivers import *  # noqa
        from .models import (StateMachine,
                             State,
                             Transition,
                             TransitionTask,
                             AvailableTask,)
        reversion.register(StateMachine)
        reversion.register(State)
        reversion.register(TransitionTask)
        reversion.register(AvailableTask)

        if hasattr(settings, 'WORKFLOW_AUTO_LOAD') and settings.WORKFLOW_AUTO_LOAD:
            logging.debug('Autoloading tasks.')
            try:
                from .task_runner import AvailableTaskLoader
                atl = AvailableTaskLoader()
                atl.load()
            except:
                logging.debug('Autoloading failed. If this is a migration, dont worry')
