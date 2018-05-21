"""Client stuffz.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import logging
import time

import boto3
from botocore import exceptions


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class Gateway(object):

    """Kodi Command, Response marshalling.

    Handles retries to provide a synchronous-like command and response interface
    to MQTT connected Kodi Thing.

    """

    IOT = boto3.client('iot-data', region_name='ap-southeast-2')

    MAX_RETRIES = 10

    def command(self, thing, rpc, asynchronous=False):
        """Issues specified RPC to specified Kodi Thing.

        Args:
            thing (str): Thing name.
            rpc (str): JSON RPC command payload.

        Returns:
            str: JSON RPC Response payload empty if fail.
        """
        try:
            cmd = json.loads(rpc)
        except (ValueError, TypeError):
            LOG.exception('invalid RPC %s', rpc)
            return {}

        shadow = self.get_shadow(thing)

        if 'desired' in shadow['state']: # pending command let's clean it up
            try:
                self.IOT.delete_thing_shadow(thingName=thing)
            except exceptions.ClientError:
                LOG.exception('problem deleting shadow for %s', thing)
                return {}

        # issue command
        state = {'state': {'desired': cmd}}
        shadow = self.update_shadow(thing, state)

        # verify dispatch
        if shadow['state'] != state['state']:
            LOG.error('failed to dispatch RPC %s', state)
            return {}

        if asynchronous:
            return shadow['state']['desired']

        # poll shadow to get reported result
        retries = 0
        while 'desired' in shadow['state'] and retries < self.MAX_RETRIES:
            shadow = self.get_shadow(thing)
            retries += 1
            time.sleep(2**retries * 0.001)
        LOG.info('attempted %d times', retries)

        if retries == self.MAX_RETRIES:
            LOG.error('maximum retries exceeded')
            return {}

        return shadow['state']['reported']['result']

    def get_shadow(self, thing):
        """Returns specified thing's shadow.

        Args:
            thing (str): Thing name.

        Returns:
            dict: Representing Shadow empty if fail.

        """
        try:
            shadow = self.IOT.get_thing_shadow(thingName=thing)
        except exceptions.ClientError:
            LOG.exception('failed to retrieve %s shadow', thing)
            return {}
        return json.loads(shadow['payload'].read())

    def update_shadow(self, thing, payload):
        """Update specified Thing's shadow with specified payload.

        Args:
            thing (str): Thing name.
            payload (dict): State information payload.

        Returns:
            dict: Representing Shadow empty if fail.

        """
        try:
            params = {'thingName':thing, 'payload':json.dumps(payload)}
            shadow = self.IOT.update_thing_shadow(**params)
        except (exceptions.ClientError, ValueError, TypeError):
            LOG.exception('failed to update %s shadow: %s', thing, payload)
            return {}
        return json.loads(shadow['payload'].read())


def main():
    """Main Program.
    """
    command = {
        'jsonrpc': '2.0',
        'params': {
            'limits': {
                'start': 0,
                'end': 1
            },
            'sort': {
                'order': 'ascending',
                'method': 'title',
                'ignorearticle': True
            },
            'filter': {
                'or': [
                    {
                        'operator': 'contains',
                        'field': 'title',
                        'value': 'Herp'
                    }
                ]
            },
            'properties': ["title"]
        },
        'method': 'VideoLibrary.GetMovies',
        'id': 1
    }

    rpc = Gateway()

    response = rpc.command('kodi', json.dumps(command))
    print response
    if 'movies' in response:
        movie_id = response['movies'][0]['movieid']
        play = {
            'jsonrpc': '2.0',
            'method': 'Player.Open',
            'id': 1,
            'params': {
                "item": {
                    "movieid":movie_id
                },
                'options': {'resume': True},
            }
        }
        response = rpc.command('kodi', json.dumps(play), asynchronous=True)
        print 'this is the response: ', response


if __name__ == '__main__':
    main()
