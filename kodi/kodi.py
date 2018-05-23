"""Client stuffz.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

import boto3


LOG = logging.getLogger(__name__)


class Kodi(object):

    """A Kodi device thing abstraction.

    Args:
        name (str): AWS IoT Kodi Thing name.

    """

    IOT = boto3.client('iot', region_name='ap-southeast-2')

    def __init__(self, thing):
        self._thing = thing

    @staticmethod
    def find_devices():
        """Return a generator of Kodi's.

        TODO: handle pagination.

        """
        rsp = Kodi.IOT.list_things(thingTypeName='Kodi', maxResults=250)
        for thing in rsp.get('things', []):
            yield Kodi(thing)

    @property
    def arn(self):
        """ARN of Kodi Thing."""
        return self._thing['thingArn']

    @property
    def name(self):
        """Name of Kodi Thing."""
        return self._thing['thingName']
