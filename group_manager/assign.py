import argparse
import os.path
from datetime import datetime
from typing import List

from GroupAssignment import GroupAssignment
from XMLConfig import XMLConfig
from adtools import utils
from adtools.objects import User
from stamdata3.StamdataExceptions import ResourceNotFound
from stamdata3.stamdata3 import Stamdata3

parser = argparse.ArgumentParser(description='Assign groups')

parser.add_argument('--groups', dest='groups', nargs='?',
                    help='Group configuration file', required=True)
parser.add_argument('--config', metavar='C', type=str, nargs='?',
                    help='Base configuration file', required=False)

args = parser.parse_args()
args = vars(args)

config_folder = os.path.join(os.path.dirname(__file__), 'config')
if args['config']:
    if os.path.isfile(args['config']):
        config_file = os.path.realpath(args['config'])
    else:
        config_file = os.path.join(config_folder, args['config'])
else:
    config_file = os.path.join(config_folder, 'config.xml')

if not os.path.exists(config_file):
    raise FileNotFoundError(config_file)

if args['groups']:
    if os.path.isfile(args['groups']):
        group_config_file = os.path.realpath(args['groups'])
    else:
        group_config_file = os.path.join(config_folder, args['groups'])
else:
    group_config_file = os.path.join(config_folder, 'config_groups.xml')

if not os.path.exists(group_config_file):
    raise FileNotFoundError(group_config_file)

config = XMLConfig(config_file)
stamdata = Stamdata3(config.file('files/stamdata3'))
org_ignore = config.list('ignore/organisation')
ou_ignore = config.list('ignore/ou')

log_folder = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(log_folder):
    os.mkdir(log_folder)

log_file = os.path.join(log_folder,
                        'Group assignment %s %s.log' % (datetime.now().strftime('%Y-%m-%d %H%M'),
                                                        os.path.basename(group_config_file))
                        )

assignment = GroupAssignment(log_file, config_file, group_config_file)

ous = assignment.get_child_ous()
for ou in ous:
    if ou['dn'] in ou_ignore:
        continue

    users: List[User] = assignment.ad.search(
        ou['dn'],
        '(employeeId=*)',
        attributes=['memberOf',
                    'employeeId',
                    'displayName',
                    'samAccountName',
                    'postalCode',
                    ], pagination=True)

    if not users:
        continue
    for user in users:
        if utils.ou(user['dn']) in ou_ignore:
            assignment.ad.log('Ignoring %s in ignored OU' % user['dn'])
            continue

        if user.element['attributes']['postalCode'] and user.element['attributes']['postalCode'][0] == 'M':
            assignment.ad.log('Ignoring %s with ignore flag' % user['dn'])
            continue

        try:
            resource = stamdata.resource(user.numeric('employeeID'))
        except ResourceNotFound as e:
            assignment.ad.log('User %s is not employed, remove all managed groups' % (
                user['attributes']['displayName']))

            assignment.remove_all_groups(user)

            continue
        try:
            main = resource.main_position()
        except AttributeError as e:
            assignment.ad.log(e)
            continue

        org = main.relation('ORGANIZATIONAL_UNIT')
        user_groups = assignment.get_groups(resource.main_position(), resource.employments)

        assignment.assign_groups(user, user_groups)
