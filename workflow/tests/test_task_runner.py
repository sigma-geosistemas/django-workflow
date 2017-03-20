# coding: utf-8
from django.db import models
from django.test import TransactionTestCase, override_settings
from workflow.task_runner import (TaskLoader,)
from django_fake_model import models as fake_models
from workflow.task_runner import TaskRunner
from workflow.tasks import BaseTask, ValidateSchemaTask
from workflow.models import (StateMachine,
                             State,
                             AvailableTask,
                             TransitionTask,
                             Transition,
                             TransitionLog,
                             StateController,
                             StateControllerData,
                             StateControllerMixIn, )
from celery.result import AsyncResult
from celery import current_app


class FakeControlled(StateControllerMixIn,
                     fake_models.FakeModel):

    foo = models.CharField(max_length=10)


# class MockValidation(ValidateSchemaTask):
class MockValidation(BaseTask):
    name = 'validationa'

    def _run(self):
        return False


class MockClassA(BaseTask):
    name = 'mocka'
    validation_class = 'workflow.tests.test_task_runner.MockValidation'

    def _run(self):
        return True


class MockClassB(BaseTask):
    name = 'mockb'
    validation_class = 'workflow.tests.test_task_runner.MockValidation'

    def _run(self):
        return True


current_app.tasks.register(MockValidation)
current_app.tasks.register(MockClassA)
current_app.tasks.register(MockClassB)


class TaskLoaderTestCase(TransactionTestCase):

    def test_initialize(self):

        tl = TaskLoader()
        self.assertIsNotNone(tl)

    def test_load_class(self):

        tl = TaskLoader()
        task = 'workflow.tests.test_task_runner.MockClassA'
        mockClass = tl.load_task(task)
        instance = mockClass()
        self.assertIsInstance(instance, mockClass)
        self.assertIsInstance(instance, MockClassA)

    def test_load_class_fail(self):

        tl = TaskLoader()
        task = 'foo.bar.baz'
        try:
            tl.load_task(task)
            self.fail('load_task should fail for foo.bar.baz')
        except:
            pass


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@FakeControlled.fake_me
class TaskRunnerTestCase(TransactionTestCase):

    def test_init(self):

        state_a = State.objects.create(code='foo', description='foo')
        state_b = State.objects.create(code='bar', description='bar')
        machine = StateMachine.objects.create(name='machine',
                                              initial_state=state_a)

        transition = Transition.objects.create(machine=machine,
                                               from_state=state_a,
                                               to_state=state_b)
        at = AvailableTask.objects.create(name='foo', klass='workflow.tests.test_task_runner.MockClassA')
        transition = TransitionTask.objects.create(transition=transition,
                                                   task=at)

        fake = FakeControlled()
        fake.save(state_machine=machine)

        runner = TaskRunner(fake, state_b)
        self.assertIsNotNone(runner)
        self.assertEqual(runner.controller.id, fake.controller.id)
        self.assertEqual(runner.controlled.id, fake.id)
        self.assertEqual(runner.transition.id, transition.id)
        self.assertEqual(2, len(runner.tasks))
        self.assertEqual(1, len(runner.validation_tasks))
        self.assertIsInstance(runner.task_loader, TaskLoader)

    def test_invalid_transition(self):
        state_a = State.objects.create(code='foo', description='foo')
        state_b = State.objects.create(code='bar', description='bar')
        machine = StateMachine.objects.create(name='machine', initial_state=state_a)

        transition = Transition.objects.create(machine=machine,
                                               from_state=state_a,
                                               to_state=state_b)
        at = AvailableTask.objects.create(name='foo',
                                          klass='workflow.tests.test_task_runner.MockClassA')
        transition = TransitionTask.objects.create(transition=transition,
                                                   task=at)

        fake = FakeControlled()
        fake.save(state_machine=machine)

        try:
            TaskRunner(fake, state_a)
            self.fail('Impossible Task Runner')
        except ValueError:
            pass

    def test_invalid_task(self):
        state_a = State.objects.create(code='foo', description='foo')
        state_b = State.objects.create(code='bar', description='bar')
        machine = StateMachine.objects.create(name='machine',
                                              initial_state=state_a)

        transition = Transition.objects.create(machine=machine,
                                               from_state=state_a,
                                               to_state=state_b)
        at = AvailableTask.objects.create(name='foo', klass='foo.bar.baz')
        transition = TransitionTask.objects.create(transition=transition,
                                                   task=at)

        fake = FakeControlled()
        fake.save(state_machine=machine)
        try:
            TaskRunner(fake, state_b)
            self.fail('problem with task loading')
        except ValueError:
            pass

    def test_run(self):
        state_a = State.objects.create(code='foo', description='foo')
        state_b = State.objects.create(code='bar', description='bar')
        machine = StateMachine.objects.create(name='machine',
                                              initial_state=state_a)

        transition = Transition.objects.create(machine=machine,
                                               from_state=state_a,
                                               to_state=state_b)
        at1 = AvailableTask.objects.create(name='foo', klass='workflow.tests.test_task_runner.MockClassA')
        at2 = AvailableTask.objects.create(name='bar', klass='workflow.tests.test_task_runner.MockClassB')
        transition = TransitionTask.objects.create(transition=transition,
                                                   task=at1)

        fake = FakeControlled()
        fake.save(state_machine=machine)

        runner = TaskRunner(fake, state_b)
        result = runner.run()
        self.assertIsInstance(result, AsyncResult)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_run_two_tasks(self):
        state_a = State.objects.create(code='foo', description='foo')
        state_b = State.objects.create(code='bar', description='bar')
        machine = StateMachine.objects.create(name='machine',
                                              initial_state=state_a)

        transition = Transition.objects.create(machine=machine,
                                               from_state=state_a,
                                               to_state=state_b)
        at1 = AvailableTask.objects.create(name='foo', klass='workflow.tests.test_task_runner.MockClassA')
        at2 = AvailableTask.objects.create(name='bar', klass='workflow.tests.test_task_runner.MockClassB')
        transition_a = TransitionTask.objects.create(transition=transition,
                                                     task=at1,
                                                     order=0)
        transition_b = TransitionTask.objects.create(transition=transition,
                                                     task=at2,
                                                     order=1)

        fake = FakeControlled()
        fake.save(state_machine=machine)

        runner = TaskRunner(fake, state_b)
        result = runner.run()
        self.assertIsInstance(result, AsyncResult)
        fake = FakeControlled.objects.all()[0]
        self.assertEqual(fake.current_state.id, state_b.id)
