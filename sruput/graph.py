import sruput
import yaml
import os
from typing import Any


class Value:
    """
    Value is a Node value.

    We need such placeholder because we use node path to refer to a value of the node,
    such as `meta.image`.
    """

    def __init__(self, value) -> None:
        self.type = type(value)
        self.v = value


class Operator:
    """
    Generic operators.

    The actual implementation of the operator lies in modules/plugins.
    Create a plugin and then register using static method register_operator
    """

    operator_types = {}
    scalar_types = (bool, int, float, str)

    def __init__(self, sruput: 'Sruput', operator_definition) -> None:
        self.definition = operator_definition
        self.output = None
        self.sruput = sruput

    def process(self):
        pass

    @classmethod
    def register_operator(cls, name, clazz):
        cls.operator_types.update(name, clazz)

    @classmethod
    def instantiate_operator(cls, sruput: 'Sruput', operator_definition: dict) -> 'Operator':
        # if type key is None, this is default scalar type
        if isinstance(operator_definition, Operator.scalar_types):
            # convert to scalar type
            operator_definition = {
                'type': 'scalar',
                'scalar': operator_definition
            }
        type_key = operator_definition.get('type', 'scalar')
        # TODO: error handling for debugging purposes if operator type was not
        #       registered
        operator_class = cls.operator_types[type_key]
        return operator_class(sruput, operator_definition)


class Node:
    """
    Node is a unit in Sruput graph that stores information of:

    - It's scalar values (can be Node again or primitives, such as numbers and string)
    - A flag that tells if the node is already evaluated or not
    - Initial parameter of the node
    - List of operators to test

    Node can be referred from a graph by following it's link.
    Resolving path such as 'meta.image' means it is iterating 'meta' node and 'image' node connected inside the 'meta' node
    """

    def __init__(self, sruput: 'Sruput', node_definition) -> None:
        self._sruput: Sruput = sruput
        self._nodes: dict = {}
        self._operators: list = []
        self._evaluated: bool = False
        self._initial_param: Value = None
        self._value: Value = None
        self._node_definition = node_definition
        self.parse_definition(node_definition)
    
    def __getattribute__(self, name: str) -> Any:
        if name.startswith('_'):
            return super().__getattribute__(name)
        elif name in self._nodes.keys():
            return self._nodes[name]
        return super().__getattribute__(name)

    def add_node(self, name: str, node: 'Node'):
        self._nodes.update({
            name: node
        })
    
    def add_operator(self, op: Operator):
        self._operators.append(op)
    
    def evaluate(self):
        """
        Evaluate, or reevaluate if needed to
        """
        # Initial param has to be a scalar
        v = self._initial_param
        if self._nodes:
            for __, n in self._nodes.items():
                n: Node
                if not n._evaluated:
                    n.evaluate()
            v = Value(self._node_definition)
            self.set_value(v)
        # If node contains operators, solve that first
        if self._operators:
            output = None
            for op in self._operators:
                op: Operator
                completed = op.process()
                if completed:
                    output = op.output
                    # We break because operators are executed as OR functions/rules
                    break
            v = Value(output)
            self.set_value(v)
        self._evaluated = True
        

    def set_initial_param(self, value):
        self._initial_param = value
    
    def set_value(self, value: Value):
        self._value = value

    def __str__(self) -> str:
        """
        Str method is the main way to chain node values in a lazy way.

        For example, this node:

        ```yaml
        version: '1.0.0'
        full-version: 'my-app-v{param.version}'
        ```

        The f-string {param.version} will cause `param` node to iterate `version` node,
        then output the string of the value stored in the node
        """
        if not self._evaluated:
            self.evaluate()
        return str(self._value.v)

    def __int__(self) -> int:
        """
        Same purposes as __str__ , but this one is for `int` type
        """
        if not self._evaluated:
            self.evaluate()
        return int(self._value.v)
    
    def __float__(self) -> float:
        """
        Same purposes as __str__ , but this one is for `float` type
        """
        if not self._evaluated:
            self.evaluate()
        return float(self._value.v)
    
    def __bool__(self) -> bool:
        """
        Same purposes as __str__ , but this one is for `bool` type
        """
        if not self._evaluated:
            self.evaluate()
        return bool(self._value.v)

    def parse_definition(self, node_definition):
        if node_definition == None:
            # If no value specified, then this is just a declaration
            self.set_value(Value(None))
        if isinstance(node_definition, Operator.scalar_types):
            # Treat it as scalar operators
            node_definition = [{
                'scalar': node_definition
            }]
        if isinstance(node_definition, dict):
            # If it is a map, then there must be subkeys
            for k, n in node_definition.items():
                node = Node(self._sruput, n)
                self.add_node(k, node)
            
            # Set node_definition as the value
            self.set_value(Value(node_definition))
        if isinstance(node_definition, list):
            # If it is an array, then this is a list of operators
            for i in node_definition:
                op = Operator.instantiate_operator(self._sruput, i)
                self.add_operator(op)


class Sruput:
    """
    Sruput is basically a graph with the following rules:

    - YAML key is a node that will contain a scalar values as output (can be string, integer)
    - If a YAML key is an array, that means the node contains an array that corresponds to an OR based rules (operator)
    - Each operator is basically a processor that received input and produces output. If it produces output, the scalar value 
      of the node is set to match with any operator that returns values in the order specified in the array.
    - Operator can be cascaded if their input is also an operator
    - Operator can use the scalar values of the node defined in the graph. If it hasn't got any values yet, then it will evaluate 
      that node first.
    """

    def __init__(self) -> None:
        self.config_objects = []
        self.initial_params = {}
        self.params = {}
        self.github = {}
        self.env = os.environ
    
    def set_github_context(self, github):
        self.github = github

    def process_initial_params(self, initial_params):
        self.initial_params.update(initial_params)

    def process(self):
        pass

    def load_config(self, config_file):
        with open(config_file) as c:
            config = yaml.load(c)
            self.config_objects.append(config)
    
    def merge_config(self):
        for c in self.config_objects:
            self.params.update(c)
    
    def send_outputs(self):
        pass