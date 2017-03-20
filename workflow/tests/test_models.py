# coding: utf-8
from django.db import models
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django_fake_model import models as fake_models
from model_mommy import mommy
from workflow.models import (StateMachine,
                             State,
                             Transition,
                             TransitionLog,
                             StateController,
                             StateControllerData,
                             StateControllerMixIn, )
User = get_user_model()


class FakeTicket(StateControllerMixIn,
                 fake_models.FakeModel):

    foo = models.CharField(max_length=10)


@FakeTicket.fake_me
class StateControllerMixInTestCase(TransactionTestCase):

    def test_initialize_signal_does_not_fire(self):

        fake = FakeTicket()
        fake.save()

        self.assertEquals(0, StateController.objects.all().count())
        self.assertEquals(0, StateControllerData.objects.all().count())

    def test_initialize_signal_fire(self):

        state = State.objects.create(code='foo', description='foo')
        machine = StateMachine.objects.create(name='machine', initial_state=state)

        fake = FakeTicket()
        fake.save(state_machine=machine)

        self.assertEquals(1, StateController.objects.all().count())
        self.assertEquals(1, StateControllerData.objects.all().count())
        self.assertEquals(1, TransitionLog.objects.all().count())

        controller = StateController.objects.all()[0]
        self.assertEquals(machine.id, controller.machine_id)
        self.assertEquals(state.id, controller.current_state_id)

        data = StateControllerData.objects.all()[0]
        self.assertEquals(data.controller_id, controller.id)
        self.assertEquals(data.state_id, controller.current_state_id)
        self.assertEquals(data.state_id, state.id)

        log = TransitionLog.objects.all()[0]
        self.assertEquals(controller.id, log.controller_id)
        self.assertIsNone(log.from_state)
        self.assertEquals(state.id, log.to_state_id)

    def test_mixin_methods_exist(self):

        state = State.objects.create(code='foo', description='foo')
        machine = StateMachine.objects.create(name='machine', initial_state=state)

        fake = FakeTicket(foo='oi')
        fake.save(state_machine=machine)

        self.assertDictEqual({}, fake.current_data.data)
        self.assertEqual(state.id, fake.current_state.id)


class TransitionModelTestCase(TransactionTestCase):

    def test_transition_without_permissions(self):

        state_a = State.objects.create(code='foo', description='foo')
        state_b = State.objects.create(code='bar', description='bar')        
        machine = StateMachine.objects.create(name='machine')
        user = mommy.make(User)
        transition_ab = Transition.objects.create(machine=machine,
                                                  from_state=state_a,
                                                  to_state=state_b)

        self.assertTrue(transition_ab.is_available(user))

    def test_transition_available(self):

        state_a = State.objects.create(code='foo', description='foo')
        state_b = State.objects.create(code='bar', description='bar')
        state_c = State.objects.create(code='baz', description='baz')
        machine = StateMachine.objects.create(name='machine')
        perm_ab = Permission.objects.all()[0]
        perm_bc = Permission.objects.all()[1]

        transition_ab = Transition.objects.create(machine=machine,
                                                  from_state=state_a,
                                                  to_state=state_b)
        transition_ab.permissions.add(perm_ab)

        transition_bc = Transition.objects.create(machine=machine,
                                                  from_state=state_b,
                                                  to_state=state_c)
        transition_bc.permissions.add(perm_bc)

        user = mommy.make(User)
        user.user_permissions.add(perm_ab)

        self.assertTrue(transition_ab.is_available(user))
        self.assertFalse(transition_bc.is_available(user))
        self.assertEqual(1, len(machine.next_for_user(state_a, user)))
