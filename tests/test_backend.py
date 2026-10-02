import unittest
from unittest.mock import patch
from miku.backend import layer_rects, normalize_rects, logical_size, NotificationSource
from miku.config import DEFAULTS

class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.mon=dict(name='DP-2',id=1,x=1920,y=0,width=2560,height=1440,scale=2,transform=0)
    def test_layers_use_local_logical_coordinates(self):
        layers={'DP-2':{'levels':{'3':[dict(namespace='notifications',address='a',x=800,y=500,w=400,h=180)]}}}
        r=layer_rects(layers,self.mon,['notifications'])[0]
        self.assertEqual((r['left'],r['top'],r['right']),(800,500,1200))
    def test_fullscreen_canvas_is_not_a_popup(self):
        layers={'DP-2':{'levels':{'3':[dict(namespace='notifications',x=0,y=0,w=1280,h=720)]}}}
        self.assertEqual(layer_rects(layers,self.mon,['notifications']),[])
    def test_ignores_hidden_or_unrecognized(self):
        layers={'DP-2':{'levels':{'3':[dict(namespace='notifications',x=10,y=200,w=300,h=80,alpha=0),dict(namespace='launcher',x=10,y=200,w=300,h=80)]}}}
        self.assertEqual(layer_rects(layers,self.mon,['notifications']),[])
    def test_rotation(self):
        self.assertEqual(logical_size(dict(self.mon,transform=1)),(720,1280))
    def test_rejects_bad_rectangles(self):
        bad=[{},None,dict(id='x',left=0,right=200,top=float('nan'),bottom=400),dict(id='x',left=400,right=100,top=200,bottom=300)]
        self.assertEqual(normalize_rects(bad,1920,1080),[])
    def test_custom_bridge_no_shell_interpolation(self):
        cfg=dict(DEFAULTS,notificationBridgeCommand=['/test adapter','{monitor}'])
        with patch('miku.backend.query',return_value=[]) as q:
            rects,adapter=NotificationSource().rects(self.mon,{},cfg)
        q.assert_called_once_with(['/test adapter','DP-2'],.4)
        self.assertEqual(adapter,'custom-bridge')
    def test_dead_midnight_does_not_spawn_each_frame(self):
        source=NotificationSource()
        with patch('miku.backend.query',side_effect=RuntimeError('absent')) as q:
            source.rects(self.mon,{},DEFAULTS)
            source.rects(self.mon,{},DEFAULTS)
        self.assertEqual(q.call_count,2)
    def test_bridge_takes_priority_even_when_empty(self):
        with patch('miku.backend.query',return_value=[]):
            self.assertEqual(NotificationSource().rects(self.mon,{},DEFAULTS),([], 'midnight-bridge'))
