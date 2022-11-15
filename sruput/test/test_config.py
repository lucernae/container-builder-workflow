import sruput
from unittest import TestCase


class ArgParseTest(TestCase):

    def test_argument_parse(self):
        parser = sruput.command_parser()

        args = parser.parse_args([
            "sruput.yaml\nsruput.override.yaml",
            """
meta:
    version: 1.2.3
author: 'Rizky Maulana Nugraha'
            """,
            "--github",
            "{'github': 'some-string'}'"
        ])

        print(args)