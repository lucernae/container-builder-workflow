from sruput.sruput import Operator


class Scalar(Operator):
    
    def __init__(self, operator_definition: dict) -> None:
        super().__init__(operator_definition)
        self.scalar = operator_definition.get('scalar', None)
    
    def process(self):
        """
        Scalar operators have basic function to evaluate scalars.

        Scalars can be literal, expressions, or f-strings.
        Those needs context to be evaluated.

        Basic context are:

        github: GitHub Action context
        env: Environment Variables
        params: Sruput parameters (the evaluated `sruput.yaml` file)
        """
        github = self.sruput.github.github
        env = self.sruput.env
        params = self.sruput.params
        completed = False
        try:
            # treat string to be always an f-string
            if isinstance(self.scalar, str):
                value = self.scalar
                output = value.format(**locals())
            else:
                # treat everything else as literal
                output = self.scalar
            completed = True
        except:
            pass
        return completed

