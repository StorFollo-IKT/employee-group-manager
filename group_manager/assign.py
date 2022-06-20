import os.path
from typing import List

from adtools import utils
from adtools.objects import User

from GroupAssignment import GroupAssignment
from XMLConfig import XMLConfig, XMLGroupConfig
from stamdata3.StamdataExceptions import ResourceNotFound
from stamdata3.stamdata3 import Stamdata3

path = os.path.join(os.path.dirname(__file__), 'config.xml')

config = XMLConfig(path)
group_config = XMLGroupConfig(os.path.join(os.path.dirname(__file__), 'groups.xml'))

stamdata = Stamdata3(config.file('files/stamdata3'))
org_ignore = config.list('ignore/organisation')
ou_ignore = config.list('ignore/ou')

log_file = os.path.join(os.path.dirname(__file__), 'logs',
                        'Group assignment %s.log' % datetime.now().strftime('%Y-%m-%d %H%M'))

assignment = GroupAssignment(log_file)

groups = group_config.attribute_list('group', 'dn')
groups_obj = assignment.resolve_groups(groups)

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
                    'samAccountName'
                    ])

    if not users:
        continue
    for user in users:
        if utils.ou(user['dn']) in ou_ignore:
            assignment.ad.log('Ignoring %s in ignored OU' % user['dn'])
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
