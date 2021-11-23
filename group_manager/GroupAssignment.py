import os
from typing import Dict, List

from XMLConfig import XMLConfig, XMLGroupConfig
from adtools import ADToolsLog, objects
from stamdata3.Employment import Employment


class GroupAssignment:
    groups: Dict[str, objects.Group]
    """All assignable groups"""

    def __init__(self):
        config = XMLConfig(os.path.join(os.path.dirname(__file__), 'config.xml'))
        self.ad = ADToolsLog()
        self.ad.debug = True
        self.ad.connect(config.text('dc/address'), config.text('dc/username'),
                        config.text('dc/password'))

        self.config = config
        self.group_config = XMLGroupConfig(os.path.join(os.path.dirname(__file__), 'groups.xml'))
        self.group_dns = self.group_config.attribute_list('group', 'dn')
        self.groups = self.resolve_groups(self.group_dns, True)

    def get_child_ous(self):
        return self.ad.search(self.config.text('dc/root/ou'),
                              '(objectClass=organizationalUnit)',
                              search_scope='LEVEL')

    def get_groups(self, main_employment: Employment, other_employments: List[Employment]):
        """
        Get all groups the user should have
        :param main_employment:
        :param other_employments:
        :return:
        """
        groups = []
        groups += self.group_config.attribute_list('group/everyone/..', 'dn')

        main_org = main_employment.relation('ORGANIZATIONAL_UNIT').value
        groups += self.group_config.organisation_groups(main_org, 'main')

        for employment in other_employments:
            org = employment.relation('ORGANIZATIONAL_UNIT').value
            groups += self.group_config.organisation_groups(org, 'all')

        return self.resolve_groups(groups)

    def resolve_groups(self, groups, return_dict=False):
        if return_dict:
            group_objs = {}
        else:
            group_objs = []

        for group in groups:
            obj = self.ad.get_group(group)
            if obj and return_dict:
                group_objs[group] = obj
            elif obj and not return_dict:
                group_objs.append(obj)
            else:
                print('Unknown group: %s' % group)
        return group_objs

    def assign_groups(self, user: objects.User, expected_groups: List[objects.Group]):
        """
        Assign groups to a user and remove unassigned groups
        :param user: User object
        :param expected_groups: All groups the user should have
        :return:
        """

        expected_group_dns = list(map(lambda g: g.dn, expected_groups))

        for group in self.groups.values():
            if group.has_member(user) and group.dn not in expected_group_dns:
                print(
                    'Managed group %s is not valid for %s with main position at %s' % (
                        group, user['displayName'], 'org'))
                group.remove_member(user)

        for group in expected_groups:
            if not group.has_member(user):
                group.add_member(user)

    def remove_all_groups(self, user: objects.User):
        """
        Remove all assignable groups from user
        :param user:
        """
        for group in self.groups.values():
            if group.has_member(user):
                group.remove_member(user)
