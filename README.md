# workflow

Django Workflow is a simple application that will allow you
to control objects state, using StateControllers.

## How it works

* Define a model that you wish to control it's state

```python
# models.py

from workflow.models import StateControllerMixIn

class Project(StateControllerMixIn):

    name = models.CharField(max_length=128)

 ```

This will override the default ```save``` of django's save, and
will force you to pass along the save method a ```state_machine```
parameter, which is a instance of StateMachine model.

If it's a new project (i.e. is being created), it will trigger
an event, initializing the state machine.

If you do not supply a state machine, this trigger will not fire
and you probably will find all sorts of errors regarding the usage
of the state machine methods.

If everything is ok, you can control your status/state using
the methods provided by the mixin, like so:

```python

state_machine = StateMachine.objects.get(name='foo') 
project = Project(name='bar)
project.save(state_machine=state_machine)

# get current state
state = project.current_state
next_state = project.next
next_available_to_user = project.next_for_user(request.user)
project.change_to(project.next)  # will fire up the transitions
```

If you wish to manage the controller directly, you can, by getting it
using the ```controller``` property that comes along with the mixin.

It shares most of these methods/proprerties.

## How to define state machines

## StateMachine

State machines are models, which have three main attributes:

* name, mandatory;
* initial_state, optional;
* representation, optional;

The name is what identifies this FSM. Initial state it's the state
that initializes this FSM. It's not required, but if you don't supply it
a bunch of bad things can happen later on, like initializing an object
that is mixed in.

representation is a JSON field that can/will hold the graphic
representation of this State Machine. You can use this attribute
to store how the chart is drawn on a front-end. This project
uses GoJS to do so. You can customize it and use another "provider".

## State

States are possible states in the FSM.

The states are not directly related to any FSM. They will be related with Transitions
that will have references to the FSM.

This means you can create multiple status and reuse them across different FSM.

```python

state_a = State(code='foo')
state_b = State(code='bar')
```

A state can have N actions. Actions are just identifiers that you
can use to control if a certain state permits certain actions.

```python

state_a = State(code='foo')
action_a = Action(name='add user')
action_b = Action(name='remove user')
state_a.actions.add(action_a)
state_a.actions.add(action_b)
```

## Transition

Transitions will control the flow of the FSM.

Each transition has a name, a state machine,
a from and to states, permissions and tasks that will
be triggered.

You can control if a certain user can execute a certain transition
by configuring the permissions field.

```python

state_a = State(code='foo')
state_b = State(code='bar')

fsm = StateMachine(name='foo', initial_state=state_a)

transition_a_b = Transition(name='fooing',
                            machine=fsm,
                            from_state=state_a,
                            to_state=state_b)

transition_b_a = Transition(name='barring',
                            machine=fsm,
                            from_state=state_b,
                            to_state=state_a)
```

## AvaliableTasks and TransitionTasks

TODO

## How it all fits together?

```
state_a = State(code='foo')
state_b = State(code='bar')

fsm = StateMachine(name='foo', initial_state=state_a)

transition_a_b = Transition(name='fooing',
                            machine=fsm,
                            from_state=state_a,
                            to_state=state_b)

transition_b_a = Transition(name='barring',
                            machine=fsm,
                            from_state=state_b,
                            to_state=state_a)

project = Project()
project.name = 'new project'
project.save(state_machine=fsm)
# this will trigger it's initialization

print project.current_state
# foo
print project.next
# bar

project.change_to(state_b)
# this will trigger all tasks registered in
# the transition_a_b. in this case, none.

project.change_to(state_a)
# this will make the project return to the
# state_a state, triggering all the tasks
# registered in transition_b_a.
```