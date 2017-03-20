# coding: utf-8
from collections import namedtuple
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Permission
from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from ordered_model.models import OrderedModel
from common.models import (DomainModelMixIn,
                           DateCreatedMixIn,
                           DateUpdatedMixIn,
                           CreatedByMixIn,
                           CompiledDescriptionMixIn, )
from .choices import (INNER_STATE_CHOICES,
                      INNER_STATE_IDLE,
                      INNER_STATE_RUNNING, )
from .signals import (before_state_change,
                      after_state_change,
                      initialize_state_machine, )


class StateMachine(DateCreatedMixIn,
                   DateUpdatedMixIn,
                   CreatedByMixIn,
                   CompiledDescriptionMixIn):

    name = models.CharField(verbose_name=_('Name'),
                            max_length=64)

    initial_state = models.ForeignKey('workflow.State',
                                      verbose_name=_('Initial State'),
                                      null=True)

    representation = JSONField(verbose_name=_('Representation'),
                               help_text=_('Graphic representation of the FSM graph in JSON.'),
                               null=True)

    def next(self, current_state):
        return self.transitions.filter(from_state=current_state)

    def next_for_user(self, current_state, user):
        transitions = self.next(current_state)
        return [t for t in transitions if t.is_available(user)]

    def __unicode__(self):

        return unicode(self.name)

    class Meta:

        verbose_name = _('State Machine')
        verbose_name_plural = _('State Machines')


class Action(DateCreatedMixIn,
             DateUpdatedMixIn,
             CreatedByMixIn):

    name = models.CharField(max_length=64,
                            verbose_name=_('Name'))

    def __unicode__(self):
        return self.name

    class Meta:

        verbose_name = _('Action')
        verbose_name_plural = _('Actions')


class State(DomainModelMixIn,
            CreatedByMixIn):

    actions = models.ManyToManyField(Action)

    class Meta:

        verbose_name = _('State')
        verbose_name_plural = _('States')


class Transition(DateCreatedMixIn,
                 DateUpdatedMixIn,
                 CreatedByMixIn):

    name = models.CharField(max_length=64,
                            verbose_name=_('Name'))

    machine = models.ForeignKey(StateMachine,
                                related_name='transitions')

    from_state = models.ForeignKey(State,
                                   related_name='from_transitions',
                                   on_delete=models.PROTECT)

    to_state = models.ForeignKey(State,
                                 related_name='to_transitions',
                                 on_delete=models.PROTECT)

    permissions = models.ManyToManyField(Permission)

    tasks = models.ManyToManyField('workflow.AvailableTask',
                                   through='workflow.TransitionTask',
                                   related_name='transitions')

    def is_available(self, user):
        '''determines if this transition can
        be executed by this user'''
        if self.permissions.all().count() <= 0:
            return True

        perms = ["{0}.{1}".format(p.content_type.app_label, p.codename)
                 for p in self.permissions.all()]

        return user.has_perms(perms)

    def __unicode__(self):

        return u'{0} - {1} > {2}'.format(self.machine,
                                         self.from_state,
                                         self.to_state)

    class Meta:

        unique_together = (('machine', 'from_state', 'to_state'), )
        verbose_name = _('Transition')
        verbose_name_plural = _('Transitions')


class AvailableTask(DateCreatedMixIn,
                    DateUpdatedMixIn,
                    CompiledDescriptionMixIn):

    name = models.CharField(verbose_name=_('Name'),
                            max_length=128)

    klass = models.CharField(verbose_name=_('Task'),
                             max_length=512)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('Available Task')
        verbose_name_plural = _('Available Tasks')


class TransitionTask(DateCreatedMixIn,
                     DateUpdatedMixIn,
                     CreatedByMixIn,
                     OrderedModel):

    transition = models.ForeignKey(Transition,
                                   related_name='transition_tasks',
                                   on_delete=models.CASCADE)

    task = models.ForeignKey(AvailableTask,
                             related_name='transition_tasks',
                             on_delete=models.CASCADE)

    def __unicode__(self):

        return unicode(self.task.klass)

    class Meta(OrderedModel.Meta):

        ordering = ('transition', 'order', )
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')


class StateController(models.Model):

    content_type = models.ForeignKey(ContentType)

    object_id = models.PositiveIntegerField()

    content_object = GenericForeignKey('content_type', 'object_id')

    machine = models.ForeignKey(StateMachine,
                                verbose_name=_('State Machine'))

    current_state = models.ForeignKey(State,
                                      verbose_name=_('Current State'),
                                      on_delete=models.PROTECT)

    task_id = models.CharField(max_length=64,
                               verbose_name=_('Task ID'),
                               help_text=_('Task ID that this controller is currently running.'),
                               null=True,
                               blank=True)

    inner_state = models.CharField(verbose_name=_('Inner State'),
                                   choices=INNER_STATE_CHOICES,
                                   default=INNER_STATE_IDLE,
                                   max_length=32)

    def next(self):

        return self.machine.transitions.filter(from_state=self.current_state)

    def can_change_to(self, next):
        '''Validates if it's a valid
        transition'''
        if self.inner_state != INNER_STATE_IDLE:
            return False

        # transitions = self.next().filter(to_state=next)

        # if transitions.count() != 1:
        #     # more then one transition is impossible
        #     return False

        return True

    def change_to(self, next):
        '''changes the state to the next one'''
        from .task_runner import TaskRunner
        if not self.can_change_to(next):
            return False

        before_state_change.send_robust(sender=self.__class__,
                                        controlled=self.content_object,
                                        controller=self,
                                        current=self.current_state,
                                        next=next)

        task_runner = TaskRunner(self, next)
        return task_runner.run()

    @property
    def current_data(self):
        return self.data.filter(state=self.current_state).latest('date_created')

    class Meta:

        unique_together = (('content_type', 'object_id'), )
        verbose_name = _('State Controller')
        verbose_name_plural = _('State Controllers')


class StateControllerData(DateCreatedMixIn,
                          DateUpdatedMixIn):

    controller = models.ForeignKey(StateController,
                                   verbose_name=_('State Controller'),
                                   related_name='data')

    state = models.ForeignKey(State,
                              verbose_name=_('State'),
                              on_delete=models.PROTECT)

    data = JSONField(verbose_name=_('State Data'),
                     default=dict)

    class Meta:

        ordering = ('-date_created', )


class StateControllerMixIn(object):

    def save(self, state_machine=None, *args, **kwargs):
        if not self.pk:
            new = True
        else:
            new = False
        super(StateControllerMixIn, self).save(*args, **kwargs)

        if new and state_machine:
            initialize_state_machine.send_robust(sender=self.__class__,
                                                 controlled=self,
                                                 state_machine=state_machine,
                                                 initial_state=state_machine.initial_state)

    @property
    def controller(self):
        content_type = ContentType.objects.get_for_model(self.__class__)
        try:
            sc = StateController.objects.get(content_type_id=content_type.id,
                                             object_id=self.id)
        except:
            return None

        return sc

    @property
    def current_data(self):
        if self.controller:
            return self.controller.current_data

    @property
    def current_state(self):
        if self.controller:
            return self.controller.current_state

        return None

    @property
    def next(self):
        if self.controller:
            return self.controller.machine.next(self.current_state)

        return None

    def next_for_user(self, user):
        if self.controller and self.controller.machine:
            return self.controller.machine.next_for_user(self.current_state,
                                                         user)
        return None

    def can_change_to(self, next):
        '''Validates if it's a valid
        transition'''
        return self.controller.can_change_to(next)

    def change_to(self, next):
        '''Changes the state machine
        to a new state and fires all the stuff it
        needs to do'''
        return self.controller.change_to(next)


class TransitionLog(DateCreatedMixIn):

    controller = models.ForeignKey(StateController,
                                   verbose_name=_('State Controller'),
                                   related_name='transition_logs')

    from_state = models.ForeignKey(State,
                                   verbose_name=_('From State'),
                                   related_name='+',
                                   null=True)

    to_state = models.ForeignKey(State,
                                 verbose_name=_('To State'),
                                 related_name='+',
                                 null=True)

    class Meta:

        verbose_name = _('Transition Log')
        verbose_name_plural = _('Transition Logs')
        ordering = ('-date_created', )
