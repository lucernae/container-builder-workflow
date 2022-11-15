from sruput.graph import Sruput
import sys
import yaml
import json
import argparse


def command_parser():
    parser = argparse.ArgumentParser(
        description='Process Sruput config file'
    )
    parser.add_argument(
        'config_files', metavar='C', nargs=1, type=str, action='store')
    parser.add_argument(
        'initial_params', metavar='P', nargs=1, type=str, action='store')
    parser.add_argument(
        '--github',type=str, action='store')
    return parser


if __name__ == '__main__':

    sruput = Sruput()

    parser = command_parser()
    args = parser.parse_args()

    try:
        config_list = args.config_files.splitlines()
        for config_file in config_list:
            sruput.load_config(config_file)
        
        sruput.merge_config()
    except:
        pass

    try:
        initial_params = yaml.load(args.initial_params)
        sruput.process_initial_params(initial_params)
    except:
        pass

    try:
        github_json = json.loads(args.github)
        sruput.set_github_context(github_json)
    except:
        pass

    sruput.process()
    sruput.send_outputs()
