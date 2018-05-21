"""Kodi Alexa Handler."""

import json
import logging
import uuid

from kodi import rpc


logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)


RPC = rpc.Gateway()


def lambda_handler(event, context):
    """Main Lambda Handler."""
    print 'event ', event
    LOG.debug('event %s', event)
    namespace = event['directive']['header']['namespace']
    if namespace == 'Alexa.Discovery':
        return handleDiscovery(context, event)
    elif namespace == 'Alexa.RemoteVideoPlayer':
        return handleRemoteVideoPlayer(context, event)
    elif namespace == 'Alexa.PlaybackController':
        return handlePlaybackController(context, event)


def handleDiscovery(context, event):
    """Handle Device Discovery.

    We could perhaps search for things of a certain 'Kodi' type.
    """
    payload = {}
    header = {
        "messageId": event['directive']['header']['messageId'],
        "name": "Discover.Response",
        "namespace": "Alexa.Discovery",
        "payloadVersion": "3"
    }

    if event['directive']['header']['name'] == 'Discover':
        payload = {
            "endpoints": [
                {
                    "capabilities": [
                        {
                            "interface": "Alexa.RemoteVideoPlayer",
                            "type": "AlexaInterface",
                            "version": "1.0"
                        },
                        {
                            "type": "AlexaInterface",
                            "interface": "Alexa.PlaybackController",
                            "version": "3",
                            "supportedOperations" : ["Play", "Pause", "Stop"]
                        }
                    ],
                    "endpointId": "videoDevice-001", # thing arn might be good
                    "description": "Kodi Media Player",
                    "displayCategories": ['OTHER'],
                    "friendlyName": "Kodi",
                    "manufacturerName": "OSMC"
                }
            ]
        }
        response = {
            'header': header,
            'payload': payload
        }
        return {'event': response}


def handleRemoteVideoPlayer(context, event):
    """Handle Request to Play Video on Kodi device."""
    payload = {}
    endpoint = event['directive']['endpoint']

    # build a video filter
    titles = []
    for entity in event['directive']['payload']['entities']:
        if entity['type'] == 'Video' or entity['type'] == 'Franchise':
            titles.append({'operator': 'contains',
                           'field': 'title',
                           'value': entity['value']
                          })
        elif entity['type'] == 'MediaType':
            pass

    command = {
        'jsonrpc': '2.0',
        'params': {
            'limits': {
                'start': 0,
                'end': 1
            },
            'sort': {
                'order': 'ascending',
                'method': 'title'
            },
            'filter': {
                'or': titles
            },
            'properties': ["title"]
        },
        'method': 'VideoLibrary.GetMovies',
        'id': 1
    }

    try:
        response = RPC.command('kodi', json.dumps(command))
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
                    'options': {
                        'resume': True
                    },
                }
            }
            response = RPC.command('kodi', json.dumps(play), asynchronous=True)
            LOG.debug('RPC response: %s', response)
    except StandardError:
        LOG.exception('Something went wrong')

    header = {
        'messageId': str(uuid.uuid1()),
        'correlationToken': event['directive']['header']['correlationToken'],
        'namespace': 'Alexa',
        'name': 'Response',
        'payloadVersion': '3'
    }
    response = {
        'header': header,
        'endpoint': endpoint,
        'payload': payload
    }
    return {'event': response}


def handlePlaybackController(context, event):
    """Handle Request Control Video on Kodi device."""
    payload = {}
    endpoint = event['directive']['endpoint']

    if event['directive']['header']['name'] == 'Stop':
        LOG.debug('Handling Stop directive')
        method = 'Player.Stop'
    elif event['directive']['header']['name'] == 'Pause':
        LOG.debug('Handling Pause directive')
        method = 'Player.PlayPause'
    elif event['directive']['header']['name'] == 'Play':
        LOG.debug('Handling Play directive')
        method = 'Player.PlayPause'

    command = {
        'jsonrpc': '2.0',
        'method': method,
        'params': {
            'playerid': 1
        },
        'id': 1
    }
    response = RPC.command('kodi', json.dumps(command), asynchronous=True)

    header = {
        'messageId': str(uuid.uuid1()),
        'namespace': 'Alexa',
        'name': 'Response',
        'payloadVersion': '3'
    }
    response = {
        'header': header,
        'endpoint': endpoint,
        'payload': payload
    }
    return {'event': response}
