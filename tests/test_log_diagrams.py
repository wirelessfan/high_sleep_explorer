"""Independently evaluate the actual SVG samples and animated point coordinates."""
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'assets/notes'
NS = {'s': 'http://www.w3.org/2000/svg'}


@pytest.mark.parametrize('name', ['intro-math-log.svg', 'math-log-inverse.svg', 'math-log-graph.svg'])
def test_drawn_curves_match_actual_function_in_linear_coordinates(name):
    svg = ET.parse(ROOT/name).getroot()
    paths = svg.findall('.//s:path[@data-function]', NS)
    assert paths
    for path in paths:
        ox, oy, sx, sy = map(float, path.attrib['data-mapping'].split())
        coords = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', path.attrib['d'])]
        kind = path.attrib['data-function']
        for px, py in zip(coords[::2], coords[1::2]):
            x, y = (px-ox)/sx, (oy-py)/sy
            expected = 2**x if kind == 'exp2' else math.log(x, 2 if kind == 'log2' else float(kind.split(':')[1]))
            assert abs(y-expected) < .005, (name, kind, x, y)


def test_intro_animation_and_static_marker_lie_on_log_curve():
    svg = ET.parse(ROOT/'intro-math-log.svg').getroot()
    dot = svg.find('.//s:circle[@id="intro-moving-point"]', NS)
    animations = {a.attrib['attributeName']: a.attrib for a in dot.findall('s:animate', NS)}
    assert animations['cx']['keyTimes'] == animations['cy']['keyTimes']
    assert animations['cx']['calcMode'] == animations['cy']['calcMode'] == 'discrete'
    for px, py in zip(map(float, animations['cx']['values'].split(';')),
                      map(float, animations['cy']['values'].split(';'))):
        assert (360-py)/46 == math.log2((px-110)/36)
    still = svg.find('.//s:circle[@class="still"]', NS)
    assert (360-float(still.attrib['cy']))/46 == math.log2((float(still.attrib['cx'])-110)/36)


def test_all_bases_pass_through_the_drawn_common_point():
    svg = ET.parse(ROOT/'math-log-graph.svg').getroot()
    dot = svg.find('.//s:circle[@id="log-common-point"]', NS)
    assert (float(dot.attrib['cx'])-130)/40 == 1
    assert (360-float(dot.attrib['cy']))/36 == 0
