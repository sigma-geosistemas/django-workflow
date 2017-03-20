# coding: utf-8
from __future__ import absolute_import
import logging
from .models import (State,
                     StateController, )
from celery import current_app
from .choices import INNER_STATE_IDLE
from .signals import after_state_change
logger = logging.getLogger(__name__)


class BaseTask(current_app.Task):

    ignore_result = False
    validation_class = ''
    name = 'Base Task'
    description = ''

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(exc.message)
        if self.controller:
            self.controller.inner_state = INNER_STATE_IDLE
            self.controller.task_id = None
            self.controller.save()

    def run(self, *args, **kwargs):
        controller_id = kwargs.pop('cid', None)
        next_id = kwargs.pop('nsi', None)
        self._load_data(controller_id, next_id)
        self.controller.task_id = self.request.get('id')
        self.controller.save()
        return self._run()

    def _load_data(self, controller_id, next_id):

        self.controller = StateController.objects.get(id=controller_id)
        self.previous = self.controller.current_state
        self.next = State.objects.get(id=next_id)

    def _run(self):

        return True


class ValidateSchemaTask(BaseTask):

    schema = None

    def _run(self):

        if self.schema:
            errors = self.schema.validate(self.controller.current_data.data)
            if len(errors) > 0:
                raise ValueError('Schema Invalid')

        return True


class ChangeStateTask(BaseTask):

    name = 'Change State'
    description = 'Changes the current state to the next.'
    public = False

    def _run(self):
        self.controller.inner_state = INNER_STATE_IDLE
        self.controller.current_state = self.next
        self.controller.task_id = None
        self.controller.save()
        after_state_change.send_robust(sender=self.controller.content_object.__class__,
                                       controlled=self.controller.content_object,
                                       controller=self.controller,
                                       previous=self.previous,
                                       current=self.next)
        return True
