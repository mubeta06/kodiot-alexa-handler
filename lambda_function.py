"""Kodi Alexa Handler."""

import logging
import uuid

import kodi


logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)


def lambda_handler(event, context):
    """Main Lambda Handler."""
    print 'event ', event
    LOG.debug('event %s', event)
    namespace = event['directive']['header']['namespace']
    if namespace == 'Alexa.Discovery':
        return handle_discovery(context, event)
    elif namespace == 'Alexa.RemoteVideoPlayer':
        return handle_remote_video_player(context, event)
    elif namespace == 'Alexa.PlaybackController':
        return handle_playback_controller(context, event)


def handle_discovery(context, event):
    """Handle Device Discovery.

    Need to ideally find device based on auth token. Need to investigate AWS
    Cognito for managing this.
    """
    payload = {}
    header = {
        "messageId": event['directive']['header']['messageId'],
        "name": "Discover.Response",
        "namespace": "Alexa.Discovery",
        "payloadVersion": "3"
    }
    token = event['directive']['payload']['scope']['token']

    if event['directive']['header']['name'] == 'Discover':
        payload = {
            'endpoints': [
                {
                    'capabilities': [
                        {
                            'interface': 'Alexa.RemoteVideoPlayer',
                            'type': 'AlexaInterface',
                            'version': '1.0'
                        },
                        {
                            'type': 'AlexaInterface',
                            'interface': 'Alexa.PlaybackController',
                            'version': '3',
                            'supportedOperations': ['Play', 'Pause', 'Stop',
                                                    'Next', 'Previous',
                                                    'FastForward', 'Rewind',
                                                    'StartOver']
                        }
                    ],
                    'endpointId': device.endpoint,
                    'description': 'Kodi Media Player',
                    'displayCategories': ['OTHER'],
                    'friendlyName': device.name,
                    'manufacturerName': 'OSMC'
                }
                for device in kodi.Kodi.find_devices(token)]
        }

        LOG.debug('found %d devices for %s', len(payload['endpoints']), token)
        response = {
            'header': header,
            'payload': payload
        }
        return {'event': response}


def handle_remote_video_player(context, event):
    """Handle Request to Play Video on Kodi device."""
    payload = {}
    endpoint = event['directive']['endpoint']
    device = kodi.Kodi.from_endpoint(endpoint['endpointId'])

    # build a video filter
    titles = []
    media_type = None # seemingly useless
    season = None
    episode = None
    for entity in event['directive']['payload']['entities']:
        if entity['type'] == 'Video' or entity['type'] == 'Franchise':
            titles.append(entity['value'])
        elif entity['type'] == 'MediaType':
            media_type = entity['value']
        elif entity['type'] == 'Season':
            season = int(entity['value'])
        elif entity['type'] == 'Episode':
            episode = int(entity['value'])

    results = device.search(titles)

    if 'movies' in results:
        device.play_movie(results['movies'][0]['movieid'])
    elif 'tvshows' in results:
        tvshowid = results['tvshows'][0]['tvshowid']
        episodeid = device.get_episode(tvshowid, season=season, episode=episode)
        if episodeid is not None:
            device.play_episode(episodeid)
        else:
            LOG.info('unable to get next unwatched episode for tvshowid %d',
                     tvshowid)
    else:
        LOG.info('could not find title %s', titles)

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


def handle_playback_controller(context, event):
    """Handle Request Control Video on Kodi device."""
    payload = {}
    endpoint = event['directive']['endpoint']
    device = kodi.Kodi.from_endpoint(endpoint['endpointId'])

    if event['directive']['header']['name'] == 'Stop':
        LOG.debug('Handling Stop directive')
        device.stop()
    elif event['directive']['header']['name'] == 'Pause':
        LOG.debug('Handling Pause directive')
        device.pause()
    elif event['directive']['header']['name'] == 'Play':
        LOG.debug('Handling Play directive')
        device.resume()
    elif event['directive']['header']['name'] == 'Next':
        LOG.debug('Handling Next directive')
        device.next()
    elif event['directive']['header']['name'] == 'Previous':
        LOG.debug('Handling Previous directive')
        device.previous()
    elif event['directive']['header']['name'] == 'FastForward':
        LOG.debug('Handling FastForward directive')
        device.fast_forward()
    elif event['directive']['header']['name'] == 'Rewind':
        LOG.debug('Handling Rewind directive')
        device.rewind()
    elif event['directive']['header']['name'] == 'StartOver':
        LOG.debug('Handling StartOver directive')
        device.seek_to_percentage(0)
    else:
        LOG.error('Unknown directive %s', event['directive']['header']['name'])

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
