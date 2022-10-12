import os.path

import lxml.etree


class XMLConfig:
    def __init__(self, file):
        self.dirname = os.path.dirname(os.path.realpath(file))
        self.config = lxml.etree.parse(file)

    def text(self, path):
        return self.config.find(path).text

    def file(self, path):
        path = self.config.find(path).text
        path = os.path.join(self.dirname, path)
        return os.path.realpath(path)

    def list(self, path):
        elements = self.config.findall(path)
        return list(map(lambda element: element.text, elements))

    def attribute_list(self, path, attribute):
        elements = self.config.findall(path)
        return list(map(lambda element: element.get(attribute), elements))


class XMLGroupConfig(XMLConfig):
    def organisation_groups(self, organisation, relation_type='main', post_code=None):
        groups = []
        
        groupsPostcode = self.config.xpath('group/%s[.="%s" and @PostCode="%s"]/..' % (relation_type, organisation, post_code))
        if relation_type == 'main' and groupsPostcode:
            groups += groupsPostcode
        else:
            groups += self.config.xpath('group/%s[.="%s" and not(@PostCode)]/..' % (relation_type, organisation))

        if not groups:
            return []

        return list(map(lambda element: element.get('dn'), groups))

    def group_exclusions(self, group_dn: str):
        """
        Check if the group excludes other groups
        :param group_dn: Group DN to check
        :return: DNs of excluded groups
        """
        groups = self.config.xpath('group[@dn="%s"]/not/group' % group_dn)
        return list(map(lambda element: element.get('dn'), groups))
