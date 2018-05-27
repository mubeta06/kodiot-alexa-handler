"""Client stuffz.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import logging

import boto3

from . import rpc


LOG = logging.getLogger(__name__)


IOT = boto3.client('iot', region_name='ap-southeast-2')


class Kodi(object):

    """A Kodi device thing abstraction.

    Args:
        name (str): AWS IoT Kodi Thing name.

    """

    def __init__(self, thing):
        self._thing = thing
        self._rpc = rpc.Gateway()

    @staticmethod
    def find_devices(token):
        """Return a generator of Kodi's.

        TODO: handle pagination. Filter by token.

        """
        rsp = IOT.list_things(thingTypeName='Kodi', maxResults=250)
        for thing in rsp.get('things', []):
            yield Kodi(thing['thingName'])

    @classmethod
    def from_endpoint(cls, endpoint):
        """Return Kodi instance for endpoint.
        """
        return cls(endpoint)

    @property
    def endpoint(self):
        """Kodi Thing name."""
        return self._thing

    @property
    def name(self):
        """Name of Kodi Thing."""
        return self._thing.title()

    @property
    def mute(self):
        """Return True if muted False otherwise."""
        command = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Application.GetProperties',
            'params': {
                'properties': ['muted']
            },
        })
        return self._rpc.command(self._thing, command)

    @mute.setter
    def mute(self, value):
        """Mute Kodi instance."""
        if not isinstance(value, bool):
            raise ValueError('mute value must be bool.')
        command = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Application.SetMute',
            'params': {
                'mute': value
            }
        })
        return self._rpc.command(self._thing, command)

    @property
    def active_player(self):
        """Return Kodi's active player or None."""
        command = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Player.GetActivePlayers'
        })
        rsp = self._rpc.command(self._thing, command)
        playerz = [item['playerid'] for item in rsp if item['type'] == 'video']
        return playerz[0] if playerz else None

    def is_playing(self, playerid=None):
        """Return a True is Video is playing False otherwise."""
        if playerid is None:
            playerid = self.active_player
        if playerid is not None:
            command = json.dumps({
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'Player.GetProperties',
                'params': {
                    'playerid': playerid,
                    'properties': ['speed']
                }
            })
            rsp = self._rpc.command(self._thing, command)
            return 'speed' in rsp and rsp['speed'] != 0
        return False

    def find_movie(self, titles):
        """Find Kodi Movie Id based on titles.

        Args:
            titles (list): List of Movie titles.

        Returns:
            int: Movie id or None if search failed.
        """
        titles = [{'operator': 'contains',
                   'field': 'title',
                   'value': title
                  } for title in titles]

        command = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'VideoLibrary.GetMovies',
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
                'properties': ['title']
            },
        })
        rsp = self._rpc.command(self._thing, command)
        return rsp['movies'][0]['movieid'] if 'movies' in rsp else None

    def play_movie(self, movie_id):
        """Play the specified Movie on Kodi instance."""
        command = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Player.Open',
            'params': {
                'item': {
                    'movieid': movie_id
                },
                'options': {'resume': True},
            }
        })
        return self._rpc.command(self._thing, command, asynchronous=True)

    def play_episode(self, episode_id):
        """Play the specified Episode on Kodi instance."""
        command = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Player.Open',
            'params': {
                'item': {
                    'movieid': episode_id
                },
                'options': {'resume': True},
            }
        })
        return self._rpc.command(self._thing, command, asynchronous=True)


    def pause(self):
        """Pause Kodi instance."""
        playerid = self.active_player
        if self.is_playing(playerid):
            self._play_pause(playerid)

    def resume(self):
        """Resume Kodi instance."""
        playerid = self.active_player
        if not self.is_playing(playerid):
            self._play_pause(playerid)

    def _play_pause(self, playerid):
        command = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Player.PlayPause',
            'params': {
                'playerid': playerid
            }
        })
        self._rpc.command(self._thing, command, asynchronous=True)

    def stop(self):
        """Stop Kodi instance."""
        playerid = self.active_player
        if playerid is not None:
            command = json.dumps({
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'Player.Stop',
                'params': {
                    'playerid': playerid
                }
            })
            self._rpc.command(self._thing, command, asynchronous=True)
