# -*- coding: utf-8 -*-

"""
Basic 3D vector operations.

Copyright (c) 2010, Renaud Blanch <rndblnch at gmail dot com>
Licence: GPLv3 or higher <http://www.gnu.org/licenses/gpl.html>
"""

# imports ####################################################################

from math import sqrt as _sqrt
from __builtin__ import sum as _sum


# vector #####################################################################

_X, _Y, _Z = _XYZ = range(3)

def vector(p1=(0., 0., 0.), p0=(0., 0., 0.)):
	return tuple(p1[i]-p0[i] for i in _XYZ)

def mul(a, v):
	return tuple(a*v[i] for i in _XYZ)

def add(u, v):
	return tuple(u[i]+v[i] for i in _XYZ)

def sum(u=vector(), *vs):
	for v in vs:
		u = add(u, v)
	return u

def sub(u, v):
	return tuple(u[i]-v[i] for i in _XYZ)

def dot(u, v):
	return _sum(u[i]*v[i] for i in _XYZ)

def cross(u, v):
	return (u[_Y]*v[_Z]-u[_Z]*v[_Y],
	        u[_Z]*v[_X]-u[_X]*v[_Z],
	        u[_X]*v[_Y]-u[_Y]*v[_X])

def norm(v):
	return _sqrt(dot(v, v))

def matrix(v):
	return [[v[i]] for i in _XYZ]
